import json
import re
import queue
from curl_cffi import requests as cffi_requests
import pandas as pd
from typing import Dict, Any, List, Tuple
from collections import defaultdict, Counter

# --- DYNAMIC STRUCTURE ANALYZER ---
class StructureAnalyzer:
    """Analyzes API response structure to dynamically determine parsing strategy"""
    
    def __init__(self, data: Dict[str, Any], log_queue: queue.Queue):
        self.data = data
        self.log_queue = log_queue
        self.markets = data.get('markets', [])
        self.selections = data.get('selections', [])
        
    def analyze_structure(self) -> Dict[str, Any]:
        """Analyze the API response structure and return insights"""
        analysis = {
            'market_fields': self._analyze_market_fields(),
            'selection_fields': self._analyze_selection_fields(),
            'patterns': self._detect_patterns(),
            'relationships': self._analyze_relationships()
        }
        
        # Log key findings
        self.log_queue.put("\n--- API Structure Analysis ---")
        self.log_queue.put(f"Markets: {len(self.markets)} found")
        self.log_queue.put(f"Selections: {len(self.selections)} found")
        
        if self.markets:
            self.log_queue.put(f"Market fields: {', '.join(analysis['market_fields']['common_fields'])}")
        if self.selections:
            self.log_queue.put(f"Selection fields: {', '.join(analysis['selection_fields']['common_fields'])}")
        
        return analysis
    
    def _analyze_market_fields(self) -> Dict[str, Any]:
        """Analyze available fields in markets"""
        if not self.markets:
            return {'common_fields': [], 'sample_values': {}}
        
        # Get all unique fields across markets
        all_fields = set()
        field_samples = defaultdict(list)
        
        for market in self.markets[:10]:  # Sample first 10
            for field, value in market.items():
                all_fields.add(field)
                if value and len(field_samples[field]) < 3:
                    field_samples[field].append(str(value)[:50])  # Truncate long values
        
        return {
            'common_fields': sorted(list(all_fields)),
            'sample_values': dict(field_samples)
        }
    
    def _analyze_selection_fields(self) -> Dict[str, Any]:
        """Analyze available fields in selections"""
        if not self.selections:
            return {'common_fields': [], 'sample_values': {}}
        
        # Get all unique fields across selections
        all_fields = set()
        field_samples = defaultdict(list)
        
        for selection in self.selections[:20]:  # Sample first 20
            for field, value in selection.items():
                all_fields.add(field)
                if value and len(field_samples[field]) < 5:
                    field_samples[field].append(str(value)[:50])
        
        return {
            'common_fields': sorted(list(all_fields)),
            'sample_values': dict(field_samples)
        }
    
    def _detect_patterns(self) -> Dict[str, Any]:
        """Detect patterns in labels and market names"""
        patterns = {
            'label_patterns': Counter(),
            'market_name_patterns': [],
            'has_points': False,
            'has_participants': False
        }
        
        # Analyze selection labels
        for sel in self.selections:
            label = sel.get('label', '')
            if label:
                patterns['label_patterns'][label] += 1
            
            # Check for points field
            if sel.get('points') is not None:
                patterns['has_points'] = True
            
            # Check for participant fields
            for field in ['participantName', 'teamName', 'playerName', 'participant']:
                if sel.get(field):
                    patterns['has_participants'] = True
                    break
        
        # Analyze market name patterns
        for market in self.markets[:10]:
            name = market.get('name', '')
            if ' - ' in name:
                patterns['market_name_patterns'].append('dash_separator')
            if any(word in name.lower() for word in ['over', 'under', 'total']):
                patterns['market_name_patterns'].append('over_under')
            if 'regular season' in name.lower():
                patterns['market_name_patterns'].append('regular_season')
        
        return patterns
    
    def _analyze_relationships(self) -> Dict[str, Any]:
        """Analyze relationships between markets and selections"""
        relationships = {
            'market_to_selections': defaultdict(list),
            'unique_market_names': set(),
            'participant_extraction': {}
        }
        
        market_names = {m['id']: m.get('name', '') for m in self.markets}
        
        for sel in self.selections[:50]:  # Analyze first 50 selections
            market_id = sel.get('marketId')
            if market_id in market_names:
                market_name = market_names[market_id]
                relationships['unique_market_names'].add(market_name)
                
                # Try to extract participant from market name
                participant = self._extract_participant_from_market(market_name, sel)
                if participant:
                    relationships['participant_extraction'][market_name] = participant
        
        return relationships
    
    def _extract_participant_from_market(self, market_name: str, selection: Dict) -> str | None:
        """Try to extract participant name from market name"""
        # First check if selection has direct participant field
        for field in ['participantName', 'teamName', 'playerName', 'participant', 'label']:
            if field in selection and selection[field] and field != 'label':
                return selection[field]
        
        # Try to extract from market name
        if ' - ' in market_name:
            return market_name.split(' - ')[0].strip()
        
        # For patterns like "Team Name Regular Season Wins"
        patterns = [
            r'^(.*?)\s+Regular Season',
            r'^(.*?)\s+Total',
            r'^(.*?)\s+to\s+',
            r'^(.*?)\s+Over',
            r'^(.*?)\s+Under'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, market_name, re.IGNORECASE)
            if match:
                participant = match.group(1).strip()
                if len(participant) > 2:  # Avoid single letters
                    return participant
        
        return None

# --- ENHANCED DYNAMIC PARSER ---
class EnhancedDynamicParser:
    """Enhanced parser that uses event data for better team/player extraction"""
    
    def __init__(self, analysis: Dict[str, Any], markets_info: Dict[int, Dict], 
                 events_info: Dict[str, Dict], market_to_event: Dict[int, str]):
        self.analysis = analysis
        self.markets_info = markets_info
        self.events_info = events_info
        self.market_to_event = market_to_event
        
    def parse_selection(self, selection: Dict, market: Dict, market_type: str) -> Dict[str, Any]:
        """Parse a single selection with enhanced context"""
        result = {
            'Subject': 'N/A',
            'Proposition': 'N/A',
            'Odds': 'N/A'
        }
        
        # Extract odds
        odds = selection.get('displayOdds', {}).get('american', '')
        result['Odds'] = odds.replace('−', '-') if odds else 'N/A'
        
        # Extract basic info
        label = selection.get('label', '')
        points = selection.get('points')
        market_name = market.get('name', 'Unknown Market')
        market_id = market.get('id')
        
        # Handle division standings specially
        if market_type == "division_standings" and label in ['1st', '2nd', '3rd', '4th']:
            # Get team info from event
            event_id = self.market_to_event.get(market_id)
            if event_id and event_id in self.events_info:
                event = self.events_info[event_id]
                participants = event.get('participants', [])
                if participants:
                    team_name = participants[0].get('name', 'Unknown Team')
                    result['Subject'] = team_name
                    result['Proposition'] = f"{label} Place"
                    return result
        
        # Handle player props with Over/Under
        if market_type == "player_props" and label in ['Over', 'Under']:
            # Extract player from market name (e.g., "Josh Allen - Regular Season Passing Yards")
            if ' - ' in market_name:
                player_name = market_name.split(' - ')[0].strip()
                prop_type = market_name.split(' - ')[1].strip()
                result['Subject'] = player_name
                result['Proposition'] = f"{prop_type} - {label} {points}" if points else f"{prop_type} - {label}"
                return result
        
        # Handle threshold markets (e.g., "2750+")
        if market_type in ["threshold", "rookie_props"] and label.endswith('+'):
            # Extract player from market name
            if ' - ' in market_name:
                player_name = market_name.split(' - ')[0].strip()
                result['Subject'] = player_name
            else:
                result['Subject'] = "Any Player"  # Default if no player specified
            result['Proposition'] = f"{market_name} - {label}"
            return result
        
        # Standard Over/Under pattern
        if label in ['Over', 'Under'] and points is not None:
            # Extract subject from market name
            subject = self._extract_subject_from_market(market_name)
            result['Subject'] = subject
            result['Proposition'] = f"{label} {points}"
            return result
        
        # Default handling
        result['Subject'] = label
        result['Proposition'] = market_name
        
        return result
    
    def _extract_subject_from_market(self, market_name: str) -> str:
        """Extract subject (team/player) from market name"""
        # Pattern for "Team Name Regular Season Wins"
        patterns = [
            (r'^(.*?)\s+Regular Season', 1),
            (r'^(.*?)\s+-\s+', 1),
            (r'^(.*?)\s+Total', 1),
            (r'^(.*?)\s+to\s+', 1),
        ]
        
        for pattern, group in patterns:
            match = re.match(pattern, market_name, re.IGNORECASE)
            if match:
                subject = match.group(group).strip()
                if len(subject) > 2:  # Avoid single letters
                    return subject
        
        # If no pattern matches, return the full market name
        return market_name

# --- ENHANCED SCRAPER WITH DYNAMIC PARSING ---
def scrape_and_parse_draftkings(log_queue: queue.Queue, league_id: str, category_id: str, 
                                subcategory_id: str, save_raw: bool = False) -> Tuple[pd.DataFrame, str, Dict]:
    """Enhanced scraper with dynamic structure analysis"""
    log_queue.put(f"Scraping DraftKings API...")
    log_queue.put(f"  League ID: {league_id}, Category ID: {category_id}, Sub-Category ID: {subcategory_id or 'None'}")
    
    api_url = f"https://sportsbook-nash.draftkings.com/api/sportscontent/dkusoh/v1/leagues/{league_id}/categories/{category_id}"
    
    try:
        response = cffi_requests.get(api_url, impersonate="chrome110", timeout=30)
        response.raise_for_status()
        data = response.json()
        log_queue.put("  Successfully fetched data feed.")
        
        # Save raw data if requested
        if save_raw:
            with open(f"raw_data_{category_id}_{subcategory_id or 'all'}.json", 'w') as f:
                json.dump(data, f, indent=2)
            log_queue.put(f"  Saved raw data to file.")
        
        # Analyze structure
        analyzer = StructureAnalyzer(data, log_queue)
        analysis = analyzer.analyze_structure()
        
        # Extract all data structures
        all_markets = data.get('markets', [])
        all_selections = data.get('selections', [])
        all_events = data.get('events', [])
        
        if not all_markets:
            log_queue.put("  No markets found in response.")
            return pd.DataFrame(), "unknown", analysis
        
        # Create mappings for enrichment
        markets_info = {market['id']: market for market in all_markets}
        events_info = {event['id']: event for event in all_events}
        
        # Create market to event mapping
        market_to_event = {}
        for market in all_markets:
            if 'eventId' in market:
                market_to_event[market['id']] = market['eventId']
        
        # Filter markets by subcategory if provided
        if subcategory_id:
            filtered_markets = [m for m in all_markets if str(m.get('subcategoryId')) == subcategory_id]
        else:
            filtered_markets = all_markets
            
        filtered_market_ids = {m['id'] for m in filtered_markets}
        
        # Filter selections by market IDs
        filtered_selections = [sel for sel in all_selections if sel.get('marketId') in filtered_market_ids]
        
        if not filtered_selections:
            log_queue.put("  No selections found for the specified criteria.")
            return pd.DataFrame(), "unknown", analysis
        
        # Detect market type based on patterns
        market_type = _detect_market_type_from_analysis(analysis, category_id)
        log_queue.put(f"  Detected market type: {market_type}")
        
        # Create enhanced parser with event data
        parser = EnhancedDynamicParser(analysis, markets_info, events_info, market_to_event)
        results = []
        
        for sel in filtered_selections:
            market_id = sel.get('marketId')
            market = markets_info.get(market_id, {})
            parsed = parser.parse_selection(sel, market, market_type)
            results.append(parsed)
        
        if not results:
            log_queue.put("  No valid betting selections parsed.")
            return pd.DataFrame(), market_type, analysis
            
        log_queue.put(f"  Parsed {len(results)} betting selections.")
        return pd.DataFrame(results), market_type, analysis
        
    except Exception as e:
        log_queue.put(f"ERROR: An error occurred.\nDetails: {e}")
        import traceback
        log_queue.put(f"Traceback: {traceback.format_exc()}")
        return pd.DataFrame(), "unknown", {}

def _detect_market_type_from_analysis(analysis: Dict[str, Any], category_id: str) -> str:
    """Detect market type from structure analysis"""
    patterns = analysis.get('patterns', {})
    label_counts = patterns.get('label_patterns', {})
    
    # Check label patterns
    total_labels = sum(label_counts.values())
    if total_labels > 0:
        over_under_ratio = (label_counts.get('Over', 0) + label_counts.get('Under', 0)) / total_labels
        if over_under_ratio > 0.8:
            # Check if it's player props based on category
            if category_id == "1759":
                return "player_props"
            return "over_under"
        
        ordinal_ratio = sum(label_counts.get(ord, 0) for ord in ['1st', '2nd', '3rd', '4th']) / total_labels
        if ordinal_ratio > 0.8:
            return "division_standings"
        
        # Check for threshold pattern
        threshold_count = sum(1 for label in label_counts if label.endswith('+'))
        if threshold_count > total_labels * 0.5:
            return "threshold"
    
    # Category-based detection
    if category_id == "1759":
        return "player_props"
    elif category_id == "1801":
        return "threshold"  # Rookie props are threshold type
    elif category_id == "820":
        return "division_standings"
    
    return "standard_futures"

# --- SMART PIVOT HANDLER ---
def apply_smart_formatting(df: pd.DataFrame, market_type: str) -> pd.DataFrame:
    """
    Apply smart formatting based on market type.
    """
    if df.empty:
        return df

    if market_type == "over_under":
        # Extract bet type and line
        extracted_data = df['Proposition'].str.extract(r'(Over|Under)\s+([+-]?[\d.]+)', expand=True)
        df['Bet'] = extracted_data[0]
        df['Line'] = extracted_data[1]

        # Drop rows where extraction failed
        df.dropna(subset=['Bet', 'Line'], inplace=True)
        if df.empty:
            return pd.DataFrame()

        # Convert to numeric
        df['Line'] = pd.to_numeric(df['Line'])
        df['Odds'] = pd.to_numeric(df['Odds'].astype(str).str.replace('−', '-'))

        # Pivot data
        line_options = df.pivot_table(
            index=['Subject', 'Line'],
            columns='Bet',
            values='Odds',
            aggfunc='first'
        ).reset_index()

        line_options.rename(columns={'Over': 'Over Odds', 'Under': 'Under Odds'}, inplace=True)
        line_options.dropna(subset=['Over Odds', 'Under Odds'], inplace=True)

        if line_options.empty:
            return pd.DataFrame()

        # Calculate cost and find main lines
        line_options['cost'] = line_options['Over Odds'].abs() + line_options['Under Odds'].abs()
        idx = line_options.groupby('Subject')['cost'].idxmin()
        main_lines = line_options.loc[idx]

        # Format final DataFrame
        main_lines = main_lines.rename(columns={'Subject': 'Participant'})
        final_cols = ['Participant', 'Line', 'Over Odds', 'Under Odds']
        
        main_lines['Over Odds'] = main_lines['Over Odds'].astype(int)
        main_lines['Under Odds'] = main_lines['Under Odds'].astype(int)

        return main_lines[final_cols].reset_index(drop=True)

    return df
