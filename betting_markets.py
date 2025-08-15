"""
Cricket Betting Markets Calculator
Calculates comprehensive betting market statistics from cricsheet JSON data
"""

import json
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional

def calculate_betting_markets(data_list: List[Dict]) -> Dict[str, Any]:
    """
    Calculate comprehensive betting market statistics from cricket match data.
    
    Args:
        data_list: List of cricket match data (JSON format)
    
    Returns:
        dict: Comprehensive betting market statistics
    """
    markets = {
        # Match outcome markets
        'match_winner': {'team_1': 0, 'team_2': 0, 'tie': 0, 'no_result': 0},
        'toss_winner': {'team_1': 0, 'team_2': 0},
        
        # Runs markets
        'total_runs': {'runs': [], 'over': 0, 'under': 0},
        'match_fours': {'fours': [], 'over': 0, 'under': 0},
        'match_sixes': {'sixes': [], 'over': 0, 'under': 0},
        'match_boundaries': {'boundaries': [], 'over': 0, 'under': 0},
        
        # Team-specific runs
        'home_total_fours': {'fours': [], 'over': 0, 'under': 0},
        'away_total_fours': {'fours': [], 'over': 0, 'under': 0},
        'home_total_sixes': {'sixes': [], 'over': 0, 'under': 0},
        'away_total_sixes': {'sixes': [], 'over': 0, 'under': 0},
        'home_total_boundaries': {'boundaries': [], 'over': 0, 'under': 0},
        'away_total_boundaries': {'boundaries': [], 'over': 0, 'under': 0},
        
        # Individual performance
        'highest_individual_score': {'scores': [], 'over': 0, 'under': 0},
        'home_highest_individual': {'scores': [], 'over': 0, 'under': 0},
        'away_highest_individual': {'scores': [], 'over': 0, 'under': 0},
        
        # Over-specific markets
        'most_runs_single_over': {'runs': [], 'over': 0, 'under': 0},
        'home_most_runs_single_over': {'runs': [], 'over': 0, 'under': 0},
        'away_most_runs_single_over': {'runs': [], 'over': 0, 'under': 0},
        
        # Wicket markets
        'home_wickets_caught': {'caught': [], 'over': 0, 'under': 0},
        'away_wickets_caught': {'caught': [], 'over': 0, 'under': 0},
        
        # Phase-wise runs
        'runs_first_6_overs': {'runs': [], 'over': 0, 'under': 0},
        'runs_first_10_overs': {'runs': [], 'over': 0, 'under': 0},
        'runs_first_15_overs': {'runs': [], 'over': 0, 'under': 0},
        
        # Wicket method markets
        'first_wicket_method': {
            'caught': 0, 'bowled': 0, 'lbw': 0, 'run_out': 0, 'stumped': 0, 'others': 0
        },
        
        # Milestone markets
        'fifty_scored': {'yes': 0, 'no': 0},
        'hundred_scored': {'yes': 0, 'no': 0},
        'home_fifty_scored': {'yes': 0, 'no': 0},
        'away_fifty_scored': {'yes': 0, 'no': 0},
        'home_hundred_scored': {'yes': 0, 'no': 0},
        'away_hundred_scored': {'yes': 0, 'no': 0},
        
        # Ball-specific markets
        'first_ball_dot': {'yes': 0, 'no': 0},
        'six_boundaries_in_over': {'yes': 0, 'no': 0},
        
        # First scoring shot
        'first_scoring_shot': {
            'single': 0, 'two': 0, 'three': 0, 'four': 0, 'six': 0, 'others': 0
        },
        
        # Additional calculated markets
        'runs_at_fall_first_wicket': {'runs': [], 'over': 0, 'under': 0},
        'total_runs_out': {'runs': [], 'over': 0, 'under': 0},
        'most_sixes': {'team_1': 0, 'team_2': 0, 'tie': 0},
        'most_fours': {'team_1': 0, 'team_2': 0, 'tie': 0},
        'highest_opening_partnership': {'partnerships': [], 'over': 0, 'under': 0, 'home_wins': 0, 'away_wins': 0, 'ties': 0},
        'most_runs_out': {'team_1': 0, 'team_2': 0, 'tie': 0}
    }
    
    for match_data in data_list:
        _process_match_for_betting_markets(match_data, markets)
    
    # Calculate over/under percentages and summary statistics
    _calculate_market_summaries(markets)
    
    return markets

def _process_match_for_betting_markets(match_data: Dict, markets: Dict) -> None:
    """Process a single match for betting market calculations."""
    info = match_data.get('info', {})
    teams = info.get('teams', [])
    
    if len(teams) < 2:
        return
    
    team_1, team_2 = teams[0], teams[1]
    
    # Match winner
    winner = info.get('outcome', {}).get('winner')
    if winner == team_1:
        markets['match_winner']['team_1'] += 1
    elif winner == team_2:
        markets['match_winner']['team_2'] += 1
    elif winner is None:
        markets['match_winner']['no_result'] += 1
    else:
        markets['match_winner']['tie'] += 1
    
    # Toss winner
    toss_winner = info.get('toss', {}).get('winner')
    if toss_winner == team_1:
        markets['toss_winner']['team_1'] += 1
    elif toss_winner == team_2:
        markets['toss_winner']['team_2'] += 1
    
    # Process innings
    match_stats = _calculate_match_stats(match_data)
    
    # Update markets with match stats
    _update_markets_with_match_stats(markets, match_stats, teams, match_data)

def _calculate_match_stats(match_data: Dict) -> Dict:
    """Calculate comprehensive statistics for a single match."""
    stats = {
        'total_runs': 0,
        'total_fours': 0,
        'total_sixes': 0,
        'total_boundaries': 0,
        'team_stats': {},
        'highest_individual_score': 0,
        'most_runs_single_over': 0,
        'first_wicket_method': None,
        'first_wicket_runs': 0,
        'first_ball_dot': False,
        'six_boundaries_in_over': False,
        'first_scoring_shot': None,
        'milestones': {'fifty': False, 'hundred': False},
        'team_milestones': {},
        'runs_first_6': 0,
        'runs_first_10': 0,
        'runs_first_15': 0,
        'total_runs_out': 0,
        'opening_partnerships': []
    }
    
    innings = match_data.get('innings', [])
    first_ball_processed = False
    
    for inning_idx, inning in enumerate(innings):
        team = inning.get('team', 'Unknown')
        
        if team not in stats['team_stats']:
            stats['team_stats'][team] = {
                'runs': 0, 'fours': 0, 'sixes': 0, 'boundaries': 0,
                'wickets_caught': 0, 'highest_individual': 0,
                'most_runs_single_over': 0, 'milestones': {'fifty': False, 'hundred': False},
                'opening_partnership': 0
            }
        
        team_stats = stats['team_stats'][team]
        
        # Track batsman scores for individual records
        batsman_scores = defaultdict(int)
        current_partnership = 0
        wickets_fallen = 0
        first_wicket_found = False
        
        for over_idx, over in enumerate(inning.get('overs', [])):
            over_runs = 0
            over_boundaries = 0
            
            for ball_idx, delivery in enumerate(over.get('deliveries', [])):
                # Skip wides and no-balls for certain calculations
                is_legal_delivery = 'extras' not in delivery or not any(
                    k in delivery['extras'] for k in ['wides', 'noballs']
                )
                
                runs = delivery['runs']['batter']
                total_runs = delivery['runs']['total']
                
                # First ball analysis
                if not first_ball_processed and is_legal_delivery:
                    stats['first_ball_dot'] = (total_runs == 0)
                    if runs > 0:
                        stats['first_scoring_shot'] = _categorize_runs(runs)
                    first_ball_processed = True
                
                # Accumulate runs
                stats['total_runs'] += total_runs
                team_stats['runs'] += total_runs
                over_runs += total_runs
                
                # Track batsman individual score
                batter = delivery.get('batter', 'Unknown')
                batsman_scores[batter] += runs
                
                # Opening partnership (first wicket)
                if wickets_fallen == 0:
                    current_partnership += runs
                
                # Boundaries
                if runs == 4:
                    stats['total_fours'] += 1
                    team_stats['fours'] += 1
                    over_boundaries += 1
                elif runs == 6:
                    stats['total_sixes'] += 1
                    team_stats['sixes'] += 1
                    over_boundaries += 1
                
                # Wickets
                if 'wickets' in delivery:
                    wickets_fallen += 1
                    
                    # First wicket analysis
                    if not first_wicket_found:
                        stats['first_wicket_runs'] = current_partnership
                        stats['opening_partnerships'].append(current_partnership)
                        team_stats['opening_partnership'] = current_partnership
                        first_wicket_found = True
                        
                        # First wicket method
                        wicket_info = delivery['wickets'][0]
                        kind = wicket_info.get('kind', 'others').lower()
                        stats['first_wicket_method'] = _categorize_wicket_method(kind)
                    
                    # Wicket method counting
                    for wicket in delivery['wickets']:
                        kind = wicket.get('kind', 'others').lower()
                        if 'caught' in kind:
                            team_stats['wickets_caught'] += 1
                
                # Phase-wise runs (first 6, 10, 15 overs) - Only for 1st innings
                if inning_idx == 0:  # Only first innings
                    if over_idx < 6:
                        stats['runs_first_6'] += total_runs
                    if over_idx < 10:
                        stats['runs_first_10'] += total_runs
                    if over_idx < 15:
                        stats['runs_first_15'] += total_runs
            
            # Check for six boundaries in over
            if over_boundaries >= 6:
                stats['six_boundaries_in_over'] = True
            
            # Track most runs in single over
            if over_runs > stats['most_runs_single_over']:
                stats['most_runs_single_over'] = over_runs
            if over_runs > team_stats['most_runs_single_over']:
                team_stats['most_runs_single_over'] = over_runs
        
        # Calculate individual scores and milestones
        if batsman_scores:
            team_highest = max(batsman_scores.values())
            team_stats['highest_individual'] = team_highest
            
            if team_highest > stats['highest_individual_score']:
                stats['highest_individual_score'] = team_highest
            
            # Check for milestones
            for score in batsman_scores.values():
                if score >= 50:
                    stats['milestones']['fifty'] = True
                    team_stats['milestones']['fifty'] = True
                if score >= 100:
                    stats['milestones']['hundred'] = True
                    team_stats['milestones']['hundred'] = True
        
        # Calculate runs out (extras)
        for over in inning.get('overs', []):
            for delivery in over.get('deliveries', []):
                stats['total_runs_out'] += delivery['runs']['extras']
    
    # Calculate boundaries
    stats['total_boundaries'] = stats['total_fours'] + stats['total_sixes']
    for team in stats['team_stats']:
        team_stats = stats['team_stats'][team]
        team_stats['boundaries'] = team_stats['fours'] + team_stats['sixes']
    
    return stats

def _update_markets_with_match_stats(markets: Dict, match_stats: Dict, teams: List[str], match_data: Dict = None) -> None:
    """Update betting markets with calculated match statistics."""
    
    # Total runs
    markets['total_runs']['runs'].append(match_stats['total_runs'])
    
    # Match boundaries
    markets['match_fours']['fours'].append(match_stats['total_fours'])
    markets['match_sixes']['sixes'].append(match_stats['total_sixes'])
    markets['match_boundaries']['boundaries'].append(match_stats['total_boundaries'])
    
    # Individual scores
    markets['highest_individual_score']['scores'].append(match_stats['highest_individual_score'])
    
    # Over-specific
    markets['most_runs_single_over']['runs'].append(match_stats['most_runs_single_over'])
    
    # Phase-wise runs
    markets['runs_first_6_overs']['runs'].append(match_stats['runs_first_6'])
    markets['runs_first_10_overs']['runs'].append(match_stats['runs_first_10'])
    markets['runs_first_15_overs']['runs'].append(match_stats['runs_first_15'])
    
    # First wicket
    if match_stats['first_wicket_runs'] > 0:
        markets['runs_at_fall_first_wicket']['runs'].append(match_stats['first_wicket_runs'])
    
    # Total runs out
    markets['total_runs_out']['runs'].append(match_stats['total_runs_out'])
    
    # Opening partnerships with match outcome tracking
    if match_stats['opening_partnerships']:
        markets['highest_opening_partnership']['partnerships'].extend(match_stats['opening_partnerships'])
        
        # Track which team won based on opening partnership performance
        if len(teams) >= 2 and match_data:
            team_1, team_2 = teams[0], teams[1]
            info = match_data.get('info', {})
            winner = info.get('outcome', {}).get('winner')
            
            # Get the opening partnership for the first innings (team that batted first)
            first_innings_team = None
            if match_data.get('innings') and len(match_data['innings']) > 0:
                first_innings_team = match_data['innings'][0].get('team')
            
            if first_innings_team and match_stats['opening_partnerships']:
                if winner == first_innings_team:
                    if first_innings_team == team_1:
                        markets['highest_opening_partnership']['home_wins'] += 1
                    else:
                        markets['highest_opening_partnership']['away_wins'] += 1
                elif winner and winner != 'No Result':
                    if first_innings_team == team_1:
                        markets['highest_opening_partnership']['away_wins'] += 1
                    else:
                        markets['highest_opening_partnership']['home_wins'] += 1
                else:
                    markets['highest_opening_partnership']['ties'] += 1
    
    # First wicket method
    if match_stats['first_wicket_method']:
        markets['first_wicket_method'][match_stats['first_wicket_method']] += 1
    
    # First ball and special events
    if match_stats['first_ball_dot']:
        markets['first_ball_dot']['yes'] += 1
    else:
        markets['first_ball_dot']['no'] += 1
    
    if match_stats['six_boundaries_in_over']:
        markets['six_boundaries_in_over']['yes'] += 1
    else:
        markets['six_boundaries_in_over']['no'] += 1
    
    # First scoring shot
    if match_stats['first_scoring_shot']:
        markets['first_scoring_shot'][match_stats['first_scoring_shot']] += 1
    
    # Milestones
    if match_stats['milestones']['fifty']:
        markets['fifty_scored']['yes'] += 1
    else:
        markets['fifty_scored']['no'] += 1
    
    if match_stats['milestones']['hundred']:
        markets['hundred_scored']['yes'] += 1
    else:
        markets['hundred_scored']['no'] += 1
    
    # Team-specific markets
    if len(teams) >= 2:
        team_1, team_2 = teams[0], teams[1]
        
        # Team stats
        team_1_stats = match_stats['team_stats'].get(team_1, {})
        team_2_stats = match_stats['team_stats'].get(team_2, {})
        
        # Home/Away designation (team_1 = home, team_2 = away)
        if team_1_stats:
            markets['home_total_fours']['fours'].append(team_1_stats.get('fours', 0))
            markets['home_total_sixes']['sixes'].append(team_1_stats.get('sixes', 0))
            markets['home_total_boundaries']['boundaries'].append(team_1_stats.get('boundaries', 0))
            markets['home_highest_individual']['scores'].append(team_1_stats.get('highest_individual', 0))
            markets['home_most_runs_single_over']['runs'].append(team_1_stats.get('most_runs_single_over', 0))
            markets['home_wickets_caught']['caught'].append(team_1_stats.get('wickets_caught', 0))
            
            if team_1_stats.get('milestones', {}).get('fifty', False):
                markets['home_fifty_scored']['yes'] += 1
            else:
                markets['home_fifty_scored']['no'] += 1
                
            if team_1_stats.get('milestones', {}).get('hundred', False):
                markets['home_hundred_scored']['yes'] += 1
            else:
                markets['home_hundred_scored']['no'] += 1
        
        if team_2_stats:
            markets['away_total_fours']['fours'].append(team_2_stats.get('fours', 0))
            markets['away_total_sixes']['sixes'].append(team_2_stats.get('sixes', 0))
            markets['away_total_boundaries']['boundaries'].append(team_2_stats.get('boundaries', 0))
            markets['away_highest_individual']['scores'].append(team_2_stats.get('highest_individual', 0))
            markets['away_most_runs_single_over']['runs'].append(team_2_stats.get('most_runs_single_over', 0))
            markets['away_wickets_caught']['caught'].append(team_2_stats.get('wickets_caught', 0))
            
            if team_2_stats.get('milestones', {}).get('fifty', False):
                markets['away_fifty_scored']['yes'] += 1
            else:
                markets['away_fifty_scored']['no'] += 1
                
            if team_2_stats.get('milestones', {}).get('hundred', False):
                markets['away_hundred_scored']['yes'] += 1
            else:
                markets['away_hundred_scored']['no'] += 1
        
        # Comparative markets
        team_1_sixes = team_1_stats.get('sixes', 0)
        team_2_sixes = team_2_stats.get('sixes', 0)
        if team_1_sixes > team_2_sixes:
            markets['most_sixes']['team_1'] += 1
        elif team_2_sixes > team_1_sixes:
            markets['most_sixes']['team_2'] += 1
        else:
            markets['most_sixes']['tie'] += 1
        
        team_1_fours = team_1_stats.get('fours', 0)
        team_2_fours = team_2_stats.get('fours', 0)
        if team_1_fours > team_2_fours:
            markets['most_fours']['team_1'] += 1
        elif team_2_fours > team_1_fours:
            markets['most_fours']['team_2'] += 1
        else:
            markets['most_fours']['tie'] += 1

def _categorize_runs(runs: int) -> str:
    """Categorize runs for first scoring shot market."""
    if runs == 1:
        return 'single'
    elif runs == 2:
        return 'two'
    elif runs == 3:
        return 'three'
    elif runs == 4:
        return 'four'
    elif runs == 6:
        return 'six'
    else:
        return 'others'

def _categorize_wicket_method(kind: str) -> str:
    """Categorize wicket method for betting markets."""
    if 'caught' in kind:
        return 'caught'
    elif 'bowled' in kind:
        return 'bowled'
    elif 'lbw' in kind:
        return 'lbw'
    elif 'run out' in kind:
        return 'run_out'
    elif 'stumped' in kind:
        return 'stumped'
    else:
        return 'others'

def _calculate_market_summaries(markets: Dict) -> None:
    """Calculate summary statistics and over/under percentages for markets."""
    
    # Define common over/under lines for different markets
    over_under_lines = {
        'total_runs': [300, 320, 340, 360, 380, 400],
        'match_fours': [40, 45, 50, 55, 60],
        'match_sixes': [8, 10, 12, 15, 18, 20],
        'match_boundaries': [50, 55, 60, 65, 70],
        'highest_individual_score': [30, 40, 50, 60, 70, 80, 90, 100],
        'most_runs_single_over': [15, 18, 20, 22, 25],
        'runs_first_6_overs': [45, 50, 55, 60],
        'runs_first_10_overs': [80, 90, 100, 110],
        'runs_first_15_overs': [130, 140, 150, 160],
        'runs_at_fall_first_wicket': [20, 25, 30, 35, 40],
        'highest_opening_partnership': [25, 30, 35, 40, 45, 50]
    }
    
    for market_name, market_data in markets.items():
        if isinstance(market_data, dict) and any(key in market_data for key in ['runs', 'fours', 'sixes', 'boundaries', 'scores', 'partnerships', 'caught']):
            # Get the data list
            data_key = None
            for key in ['runs', 'fours', 'sixes', 'boundaries', 'scores', 'partnerships', 'caught']:
                if key in market_data and isinstance(market_data[key], list) and market_data[key]:
                    data_key = key
                    break
            
            if data_key and market_data[data_key]:
                data_list = market_data[data_key]
                
                # Calculate basic statistics
                market_data['count'] = len(data_list)
                market_data['average'] = sum(data_list) / len(data_list)
                market_data['median'] = sorted(data_list)[len(data_list) // 2]
                market_data['min'] = min(data_list)
                market_data['max'] = max(data_list)
                
                # Calculate over/under percentages for predefined lines
                lines = over_under_lines.get(market_name, [market_data['average']])
                market_data['over_under_analysis'] = {}
                
                for line in lines:
                    over_count = sum(1 for value in data_list if value > line)
                    under_count = len(data_list) - over_count
                    
                    market_data['over_under_analysis'][f'line_{line}'] = {
                        'over_percentage': (over_count / len(data_list)) * 100,
                        'under_percentage': (under_count / len(data_list)) * 100,
                        'over_count': over_count,
                        'under_count': under_count
                    }

def format_betting_markets_for_display(markets: Dict) -> Dict[str, Any]:
    """Format betting markets data for display in Streamlit."""
    
    formatted = {
        'Match Outcome Markets': {
            'Match Winner': _add_percentages_to_categorical(markets['match_winner']),
            'Toss Winner': _add_percentages_to_categorical(markets['toss_winner']),
            'Most Sixes': _add_percentages_to_categorical(markets['most_sixes']),
            'Most Fours': _add_percentages_to_categorical(markets['most_fours'])
        },
        
        'Runs Markets': {
            'Total Runs': _format_numeric_market(markets['total_runs']),
            'Match Fours': _format_numeric_market(markets['match_fours']),
            'Match Sixes': _format_numeric_market(markets['match_sixes']),
            'Match Boundaries': _format_numeric_market(markets['match_boundaries'])
        },
        
        'Team Markets': {
            'Home Team Fours': _format_numeric_market(markets['home_total_fours']),
            'Away Team Fours': _format_numeric_market(markets['away_total_fours']),
            'Home Team Sixes': _format_numeric_market(markets['home_total_sixes']),
            'Away Team Sixes': _format_numeric_market(markets['away_total_sixes']),
            'Home Team Boundaries': _format_numeric_market(markets['home_total_boundaries']),
            'Away Team Boundaries': _format_numeric_market(markets['away_total_boundaries'])
        },
        
        'Individual Performance': {
            'Highest Individual Score': _format_numeric_market(markets['highest_individual_score']),
            'Home Highest Individual': _format_numeric_market(markets['home_highest_individual']),
            'Away Highest Individual': _format_numeric_market(markets['away_highest_individual'])
        },
        
        'Phase Markets': {
            'Runs First 6 Overs (1st Innings Only)': _format_numeric_market(markets['runs_first_6_overs']),
            'Runs First 10 Overs (1st Innings Only)': _format_numeric_market(markets['runs_first_10_overs']),
            'Runs First 15 Overs (1st Innings Only)': _format_numeric_market(markets['runs_first_15_overs'])
        },
        
        'Special Markets': {
            'First Wicket Method': _add_percentages_to_categorical(markets['first_wicket_method']),
            'Fifty Scored': _add_percentages_to_categorical(markets['fifty_scored']),
            'Hundred Scored': _add_percentages_to_categorical(markets['hundred_scored']),
            'Home Fifty Scored': _add_percentages_to_categorical(markets['home_fifty_scored']),
            'Away Fifty Scored': _add_percentages_to_categorical(markets['away_fifty_scored']),
            'Home Hundred Scored': _add_percentages_to_categorical(markets['home_hundred_scored']),
            'Away Hundred Scored': _add_percentages_to_categorical(markets['away_hundred_scored']),
            'First Ball Dot': _add_percentages_to_categorical(markets['first_ball_dot']),
            'Six Boundaries in Over': _add_percentages_to_categorical(markets['six_boundaries_in_over']),
            'First Scoring Shot': _add_percentages_to_categorical(markets['first_scoring_shot'])
        },
        
        'Wicket Markets': {
            'Home Wickets Caught': _format_numeric_market(markets['home_wickets_caught']),
            'Away Wickets Caught': _format_numeric_market(markets['away_wickets_caught'])
        },
        
        'Partnership Markets': {
            'Runs at Fall 1st Wicket': _format_numeric_market(markets['runs_at_fall_first_wicket']),
            'Highest Opening Partnership': _format_opening_partnership_market(markets['highest_opening_partnership'])
        }
    }
    
    return formatted

def _add_percentages_to_categorical(market_data: Dict) -> Dict:
    """Add percentages to categorical market data."""
    if not isinstance(market_data, dict):
        return market_data
    
    total = sum(market_data.values())
    if total == 0:
        return market_data
    
    result = {}
    for outcome, count in market_data.items():
        percentage = (count / total) * 100
        result[outcome] = {
            'count': count,
            'percentage': round(percentage, 1)
        }
    
    return result

def _format_opening_partnership_market(market_data: Dict) -> Dict:
    """Format opening partnership market with match outcome analysis."""
    if not market_data or 'average' not in market_data:
        return market_data
    
    result = {
        'Average': round(market_data['average'], 2),
        'Median': market_data['median'],
        'Min': market_data['min'],
        'Max': market_data['max'],
        'Sample Size': market_data['count'],
        'Over/Under Lines': market_data.get('over_under_analysis', {}),
        'Match Outcomes': {
            'Home Team Wins': market_data.get('home_wins', 0),
            'Away Team Wins': market_data.get('away_wins', 0),
            'Ties/No Results': market_data.get('ties', 0)
        }
    }
    
    # Add percentages for match outcomes
    total_matches = result['Match Outcomes']['Home Team Wins'] + result['Match Outcomes']['Away Team Wins'] + result['Match Outcomes']['Ties/No Results']
    if total_matches > 0:
        result['Match Outcome Percentages'] = {
            'Home Team Win %': round((result['Match Outcomes']['Home Team Wins'] / total_matches) * 100, 1),
            'Away Team Win %': round((result['Match Outcomes']['Away Team Wins'] / total_matches) * 100, 1),
            'Tie/No Result %': round((result['Match Outcomes']['Ties/No Results'] / total_matches) * 100, 1)
        }
    
    return result

def calculate_custom_over_under(data_list: List[float], custom_line: float) -> Dict:
    """Calculate over/under percentages for a custom line."""
    if not data_list:
        return {'error': 'No data available'}
    
    over_count = sum(1 for value in data_list if value > custom_line)
    under_count = len(data_list) - over_count
    
    return {
        'line': custom_line,
        'over_count': over_count,
        'under_count': under_count,
        'over_percentage': round((over_count / len(data_list)) * 100, 1),
        'under_percentage': round((under_count / len(data_list)) * 100, 1),
        'total_matches': len(data_list)
    }

def _format_numeric_market(market_data: Dict) -> Dict:
    """Format numeric market data for display."""
    if not market_data or 'average' not in market_data:
        return market_data
    
    return {
        'Average': round(market_data['average'], 2),
        'Median': market_data['median'],
        'Min': market_data['min'],
        'Max': market_data['max'],
        'Sample Size': market_data['count'],
        'Over/Under Lines': market_data.get('over_under_analysis', {})
    }