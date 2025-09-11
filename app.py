import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(layout="wide")

# Import betting markets functions with comprehensive error handling
BETTING_MARKETS_AVAILABLE = False
betting_markets_error = None

try:
    from betting_markets import calculate_betting_markets, format_betting_markets_for_display, calculate_custom_over_under
    BETTING_MARKETS_AVAILABLE = True
except ImportError as e:
    betting_markets_error = f"ImportError: {str(e)}"
except Exception as e:
    betting_markets_error = f"Error: {str(e)}"

# Define fallback functions if betting markets module is not available
if not BETTING_MARKETS_AVAILABLE:
    def calculate_betting_markets(data):
        return {}
    def format_betting_markets_for_display(data):
        return {}
    def calculate_custom_over_under(data, line):
        return {'error': 'Betting markets module not available'}

# --- Helper Functions ---

def calculate_team_stats(all_deliveries, team_name):
    """
    Calculate statistics for a specific team.
    
    Args:
        all_deliveries: List of delivery data
        team_name: Name of the team to analyze
    
    Returns:
        dict: Team-specific statistics
    """
    team_deliveries = [d for d in all_deliveries if d['team'] == team_name]
    
    if not team_deliveries:
        return None
    
    total_balls = len(team_deliveries)
    
    # Calculate basic statistics for the team
    team_stats = {
        'team_name': team_name,
        'total_balls': total_balls,
        'avg_runs_per_ball': sum(d['runs_off_bat'] for d in team_deliveries) / total_balls,
        'avg_run_rate': (sum(d['runs_off_bat'] for d in team_deliveries) / total_balls) * 6,
        'dot_ball_percentage': (sum(1 for d in team_deliveries if d['is_dot']) / total_balls) * 100,
        'single_percentage': (sum(1 for d in team_deliveries if d['is_single']) / total_balls) * 100,
        'four_percentage': (sum(1 for d in team_deliveries if d['is_four']) / total_balls) * 100,
        'six_percentage': (sum(1 for d in team_deliveries if d['is_six']) / total_balls) * 100,
        'wicket_percentage': (sum(1 for d in team_deliveries if d['is_wicket']) / total_balls) * 100,
        'boundary_percentage': (sum(1 for d in team_deliveries if d['is_four'] or d['is_six']) / total_balls) * 100
    }
    
    # Runs distribution for the team
    for runs in range(7):
        count = sum(1 for d in team_deliveries if d['runs_off_bat'] == runs)
        team_stats[f'runs_{runs}_probability'] = (count / total_balls) * 100
    
    # Phase-wise statistics for the team
    for phase in ['powerplay', 'middle', 'death']:
        phase_deliveries = [d for d in team_deliveries if d['phase'] == phase]
        if phase_deliveries:
            phase_balls = len(phase_deliveries)
            team_stats[f'{phase}_stats'] = {
                'balls': phase_balls,
                'avg_runs_per_ball': sum(d['runs_off_bat'] for d in phase_deliveries) / phase_balls,
                'run_rate': (sum(d['runs_off_bat'] for d in phase_deliveries) / phase_balls) * 6,
                'dot_ball_percentage': (sum(1 for d in phase_deliveries if d['is_dot']) / phase_balls) * 100,
                'single_percentage': (sum(1 for d in phase_deliveries if d['is_single']) / phase_balls) * 100,
                'four_percentage': (sum(1 for d in phase_deliveries if d['is_four']) / phase_balls) * 100,
                'six_percentage': (sum(1 for d in phase_deliveries if d['is_six']) / phase_balls) * 100,
                'wicket_percentage': (sum(1 for d in phase_deliveries if d['is_wicket']) / phase_balls) * 100
            }
        else:
            team_stats[f'{phase}_stats'] = None
    
    # Additional team-specific metrics
    wicket_balls = [d for d in team_deliveries if d['is_wicket']]
    if wicket_balls:
        team_stats['avg_balls_between_wickets'] = total_balls / len(wicket_balls)
    
    boundary_balls = [d for d in team_deliveries if d['is_four'] or d['is_six']]
    if boundary_balls:
        team_stats['avg_balls_between_boundaries'] = total_balls / len(boundary_balls)
    
    return team_stats

def calculate_venue_wise_stats(data_list):
    """
    Calculate venue-wise statistics for cricket matches.
    
    Args:
        data_list: List of cricket match data (JSON format)
    
    Returns:
        dict: Venue-wise statistics including scoring patterns, outcomes, and conditions
    """
    venue_stats = {}
    
    for data in data_list:
        venue = data.get('info', {}).get('venue', 'Unknown Venue')
        
        if venue not in venue_stats:
            venue_stats[venue] = {
                'matches': 0,
                'total_runs': 0,
                'total_balls': 0,
                'total_wickets': 0,
                'total_fours': 0,
                'total_sixes': 0,
                'total_dots': 0,
                'innings_scores': [],
                'toss_winners': [],
                'match_winners': [],
                'toss_decisions': [],
                'first_innings_scores': [],
                'second_innings_scores': [],
                'powerplay_runs': [],
                'death_over_runs': [],
                'team_totals': []
            }
        
        venue_data = venue_stats[venue]
        venue_data['matches'] += 1
        
        # Extract match info
        info = data.get('info', {})
        venue_data['toss_winners'].append(info.get('toss', {}).get('winner', 'Unknown'))
        venue_data['match_winners'].append(info.get('outcome', {}).get('winner', 'No Result'))
        venue_data['toss_decisions'].append(info.get('toss', {}).get('decision', 'Unknown'))
        
        # Process innings
        for inning_idx, inning in enumerate(data.get('innings', [])):
            inning_runs = 0
            inning_balls = 0
            inning_wickets = 0
            inning_fours = 0
            inning_sixes = 0
            inning_dots = 0
            powerplay_runs = 0
            death_over_runs = 0
            
            for over in inning.get('overs', []):
                over_num = over.get('over', 0)
                
                for delivery in over.get('deliveries', []):
                    # Skip extras for ball count
                    if 'extras' not in delivery or not any(k in delivery['extras'] for k in ['wides', 'noballs']):
                        inning_balls += 1
                        venue_data['total_balls'] += 1
                    
                    runs = delivery['runs']['batter']
                    total_runs = delivery['runs']['total']
                    
                    inning_runs += total_runs
                    venue_data['total_runs'] += total_runs
                    
                    if runs == 0:
                        inning_dots += 1
                        venue_data['total_dots'] += 1
                    elif runs == 4:
                        inning_fours += 1
                        venue_data['total_fours'] += 1
                    elif runs == 6:
                        inning_sixes += 1
                        venue_data['total_sixes'] += 1
                    
                    if 'wickets' in delivery:
                        inning_wickets += 1
                        venue_data['total_wickets'] += 1
                    
                    # Phase-wise runs
                    if over_num < 6:  # Powerplay
                        powerplay_runs += total_runs
                    elif over_num >= 15:  # Death overs
                        death_over_runs += total_runs
            
            venue_data['innings_scores'].append(inning_runs)
            venue_data['team_totals'].append(inning_runs)
            venue_data['powerplay_runs'].append(powerplay_runs)
            venue_data['death_over_runs'].append(death_over_runs)
            
            if inning_idx == 0:
                venue_data['first_innings_scores'].append(inning_runs)
            elif inning_idx == 1:
                venue_data['second_innings_scores'].append(inning_runs)
    
    # Calculate summary statistics for each venue
    venue_summary = {}
    for venue, stats in venue_stats.items():
        if stats['matches'] > 0:
            venue_summary[venue] = {
                'matches': stats['matches'],
                'avg_total_runs_per_match': sum(stats['team_totals']) / len(stats['team_totals']) if stats['team_totals'] else 0,
                'avg_runs_per_ball': stats['total_runs'] / stats['total_balls'] if stats['total_balls'] > 0 else 0,
                'avg_run_rate': (stats['total_runs'] / stats['total_balls'] * 6) if stats['total_balls'] > 0 else 0,
                'dot_ball_percentage': (stats['total_dots'] / stats['total_balls'] * 100) if stats['total_balls'] > 0 else 0,
                'four_percentage': (stats['total_fours'] / stats['total_balls'] * 100) if stats['total_balls'] > 0 else 0,
                'six_percentage': (stats['total_sixes'] / stats['total_balls'] * 100) if stats['total_balls'] > 0 else 0,
                'boundary_percentage': ((stats['total_fours'] + stats['total_sixes']) / stats['total_balls'] * 100) if stats['total_balls'] > 0 else 0,
                'wicket_percentage': (stats['total_wickets'] / stats['total_balls'] * 100) if stats['total_balls'] > 0 else 0,
                'avg_first_innings': sum(stats['first_innings_scores']) / len(stats['first_innings_scores']) if stats['first_innings_scores'] else 0,
                'avg_second_innings': sum(stats['second_innings_scores']) / len(stats['second_innings_scores']) if stats['second_innings_scores'] else 0,
                'avg_powerplay_runs': sum(stats['powerplay_runs']) / len(stats['powerplay_runs']) if stats['powerplay_runs'] else 0,
                'avg_death_over_runs': sum(stats['death_over_runs']) / len(stats['death_over_runs']) if stats['death_over_runs'] else 0,
                'highest_team_total': max(stats['team_totals']) if stats['team_totals'] else 0,
                'lowest_team_total': min(stats['team_totals']) if stats['team_totals'] else 0,
                'toss_win_match_win_rate': 0,
                'bat_first_win_rate': 0,
                'bowl_first_win_rate': 0
            }
            
            # Calculate toss and decision impact
            toss_win_match_win = sum(1 for i, winner in enumerate(stats['match_winners']) 
                                   if winner == stats['toss_winners'][i] and winner != 'No Result')
            total_decided_matches = sum(1 for winner in stats['match_winners'] if winner != 'No Result')
            
            if total_decided_matches > 0:
                venue_summary[venue]['toss_win_match_win_rate'] = (toss_win_match_win / total_decided_matches) * 100
            
            # Bat first vs bowl first success rates
            bat_first_wins = 0
            bowl_first_wins = 0
            bat_first_matches = 0
            bowl_first_matches = 0
            
            for i, decision in enumerate(stats['toss_decisions']):
                if i < len(stats['match_winners']) and stats['match_winners'][i] != 'No Result':
                    if decision == 'bat':
                        bat_first_matches += 1
                        if stats['match_winners'][i] == stats['toss_winners'][i]:
                            bat_first_wins += 1
                    elif decision == 'field':
                        bowl_first_matches += 1
                        if stats['match_winners'][i] == stats['toss_winners'][i]:
                            bowl_first_wins += 1
            
            if bat_first_matches > 0:
                venue_summary[venue]['bat_first_win_rate'] = (bat_first_wins / bat_first_matches) * 100
            if bowl_first_matches > 0:
                venue_summary[venue]['bowl_first_win_rate'] = (bowl_first_wins / bowl_first_matches) * 100
            
            # Add ball outcome probabilities for Markov chain modeling
            if stats['total_balls'] > 0:
                for runs in range(7):  # 0-6 runs
                    count = 0
                    # Count occurrences of each run outcome for this venue
                    for data in data_list:
                        if data.get('info', {}).get('venue', 'Unknown Venue') == venue:
                            for inning in data.get('innings', []):
                                for over in inning.get('overs', []):
                                    for delivery in over.get('deliveries', []):
                                        if 'extras' not in delivery or not any(k in delivery['extras'] for k in ['wides', 'noballs']):
                                            if delivery['runs']['batter'] == runs:
                                                count += 1
                    venue_summary[venue][f'runs_{runs}_probability'] = (count / stats['total_balls']) * 100 if stats['total_balls'] > 0 else 0
    
    return venue_summary

def calculate_team_wise_stats(data_list):
    """
    Calculate comprehensive team-wise statistics for cricket matches.
    
    Args:
        data_list: List of cricket match data (JSON format)
    
    Returns:
        dict: Team-wise statistics including batting, bowling, and match outcomes
    """
    team_stats = {}
    
    for data in data_list:
        info = data.get('info', {})
        teams = info.get('teams', [])
        winner = info.get('outcome', {}).get('winner', 'No Result')
        toss_winner = info.get('toss', {}).get('winner', 'Unknown')
        toss_decision = info.get('toss', {}).get('decision', 'Unknown')
        
        # Initialize team stats if not exists
        for team in teams:
            if team not in team_stats:
                team_stats[team] = {
                    'matches_played': 0,
                    'matches_won': 0,
                    'matches_lost': 0,
                    'no_results': 0,
                    'toss_won': 0,
                    'toss_won_match_won': 0,
                    'bat_first_matches': 0,
                    'bat_first_wins': 0,
                    'bowl_first_matches': 0,
                    'bowl_first_wins': 0,
                    'total_runs_scored': 0,
                    'total_runs_conceded': 0,
                    'total_balls_faced': 0,
                    'total_balls_bowled': 0,
                    'total_wickets_lost': 0,
                    'total_wickets_taken': 0,
                    'total_fours_hit': 0,
                    'total_sixes_hit': 0,
                    'total_dots_faced': 0,
                    'total_dots_bowled': 0,
                    'innings_scores': [],
                    'powerplay_runs_scored': [],
                    'powerplay_runs_conceded': [],
                    'death_over_runs_scored': [],
                    'death_over_runs_conceded': [],
                    'highest_score': 0,
                    'lowest_score': float('inf'),
                    'venues_played': set(),
                    'opponents_faced': set()
                }
        
        # Update match results
        for team in teams:
            team_stats[team]['matches_played'] += 1
            team_stats[team]['venues_played'].add(info.get('venue', 'Unknown'))
            
            # Add opponents
            opponents = [t for t in teams if t != team]
            for opponent in opponents:
                team_stats[team]['opponents_faced'].add(opponent)
            
            if winner == team:
                team_stats[team]['matches_won'] += 1
            elif winner != 'No Result' and winner in teams:
                team_stats[team]['matches_lost'] += 1
            else:
                team_stats[team]['no_results'] += 1
            
            # Toss statistics
            if toss_winner == team:
                team_stats[team]['toss_won'] += 1
                if winner == team:
                    team_stats[team]['toss_won_match_won'] += 1
                
                # Toss decision impact
                if toss_decision == 'bat':
                    team_stats[team]['bat_first_matches'] += 1
                    if winner == team:
                        team_stats[team]['bat_first_wins'] += 1
                elif toss_decision == 'field':
                    team_stats[team]['bowl_first_matches'] += 1
                    if winner == team:
                        team_stats[team]['bowl_first_wins'] += 1
        
        # Process innings data
        for inning_idx, inning in enumerate(data.get('innings', [])):
            batting_team = inning.get('team', 'Unknown')
            bowling_team = None
            
            # Find bowling team
            for team in teams:
                if team != batting_team:
                    bowling_team = team
                    break
            
            if batting_team in team_stats:
                inning_runs = 0
                inning_balls = 0
                inning_wickets = 0
                inning_fours = 0
                inning_sixes = 0
                inning_dots = 0
                powerplay_runs = 0
                death_over_runs = 0
                
                for over in inning.get('overs', []):
                    over_num = over.get('over', 0)
                    
                    for delivery in over.get('deliveries', []):
                        # Skip extras for ball count
                        if 'extras' not in delivery or not any(k in delivery['extras'] for k in ['wides', 'noballs']):
                            inning_balls += 1
                            team_stats[batting_team]['total_balls_faced'] += 1
                            if bowling_team and bowling_team in team_stats:
                                team_stats[bowling_team]['total_balls_bowled'] += 1
                        
                        runs = delivery['runs']['batter']
                        total_runs = delivery['runs']['total']
                        
                        inning_runs += total_runs
                        team_stats[batting_team]['total_runs_scored'] += total_runs
                        if bowling_team and bowling_team in team_stats:
                            team_stats[bowling_team]['total_runs_conceded'] += total_runs
                        
                        if runs == 0:
                            inning_dots += 1
                            team_stats[batting_team]['total_dots_faced'] += 1
                            if bowling_team and bowling_team in team_stats:
                                team_stats[bowling_team]['total_dots_bowled'] += 1
                        elif runs == 4:
                            inning_fours += 1
                            team_stats[batting_team]['total_fours_hit'] += 1
                        elif runs == 6:
                            inning_sixes += 1
                            team_stats[batting_team]['total_sixes_hit'] += 1
                        
                        if 'wickets' in delivery:
                            inning_wickets += 1
                            team_stats[batting_team]['total_wickets_lost'] += 1
                            if bowling_team and bowling_team in team_stats:
                                team_stats[bowling_team]['total_wickets_taken'] += 1
                        
                        # Phase-wise runs
                        if over_num < 6:  # Powerplay
                            powerplay_runs += total_runs
                        elif over_num >= 15:  # Death overs
                            death_over_runs += total_runs
                
                # Store innings data
                team_stats[batting_team]['innings_scores'].append(inning_runs)
                team_stats[batting_team]['powerplay_runs_scored'].append(powerplay_runs)
                team_stats[batting_team]['death_over_runs_scored'].append(death_over_runs)
                
                if bowling_team and bowling_team in team_stats:
                    team_stats[bowling_team]['powerplay_runs_conceded'].append(powerplay_runs)
                    team_stats[bowling_team]['death_over_runs_conceded'].append(death_over_runs)
                
                # Update highest/lowest scores
                if inning_runs > team_stats[batting_team]['highest_score']:
                    team_stats[batting_team]['highest_score'] = inning_runs
                if inning_runs < team_stats[batting_team]['lowest_score']:
                    team_stats[batting_team]['lowest_score'] = inning_runs
    
    # Calculate derived statistics
    team_summary = {}
    for team, stats in team_stats.items():
        if stats['matches_played'] > 0:
            # Convert sets to counts
            stats['venues_played'] = len(stats['venues_played'])
            stats['opponents_faced'] = len(stats['opponents_faced'])
            
            # Fix lowest score if no valid scores
            if stats['lowest_score'] == float('inf'):
                stats['lowest_score'] = 0
            
            team_summary[team] = {
                **stats,
                'win_percentage': (stats['matches_won'] / stats['matches_played']) * 100,
                'loss_percentage': (stats['matches_lost'] / stats['matches_played']) * 100,
                'toss_win_percentage': (stats['toss_won'] / stats['matches_played']) * 100,
                'toss_win_match_win_rate': (stats['toss_won_match_won'] / stats['toss_won']) * 100 if stats['toss_won'] > 0 else 0,
                'bat_first_win_rate': (stats['bat_first_wins'] / stats['bat_first_matches']) * 100 if stats['bat_first_matches'] > 0 else 0,
                'bowl_first_win_rate': (stats['bowl_first_wins'] / stats['bowl_first_matches']) * 100 if stats['bowl_first_matches'] > 0 else 0,
                'avg_score': sum(stats['innings_scores']) / len(stats['innings_scores']) if stats['innings_scores'] else 0,
                'avg_runs_per_ball': stats['total_runs_scored'] / stats['total_balls_faced'] if stats['total_balls_faced'] > 0 else 0,
                'avg_run_rate': (stats['total_runs_scored'] / stats['total_balls_faced'] * 6) if stats['total_balls_faced'] > 0 else 0,
                'strike_rate': (stats['total_runs_scored'] / stats['total_balls_faced'] * 100) if stats['total_balls_faced'] > 0 else 0,
                'dot_ball_percentage': (stats['total_dots_faced'] / stats['total_balls_faced'] * 100) if stats['total_balls_faced'] > 0 else 0,
                'boundary_percentage': ((stats['total_fours_hit'] + stats['total_sixes_hit']) / stats['total_balls_faced'] * 100) if stats['total_balls_faced'] > 0 else 0,
                'avg_powerplay_runs': sum(stats['powerplay_runs_scored']) / len(stats['powerplay_runs_scored']) if stats['powerplay_runs_scored'] else 0,
                'avg_death_over_runs': sum(stats['death_over_runs_scored']) / len(stats['death_over_runs_scored']) if stats['death_over_runs_scored'] else 0,
                'bowling_avg_runs_conceded': stats['total_runs_conceded'] / stats['total_balls_bowled'] * 6 if stats['total_balls_bowled'] > 0 else 0,
                'bowling_strike_rate': stats['total_balls_bowled'] / stats['total_wickets_taken'] if stats['total_wickets_taken'] > 0 else 0,
                'bowling_economy': stats['total_runs_conceded'] / (stats['total_balls_bowled'] / 6) if stats['total_balls_bowled'] > 0 else 0,
                'avg_powerplay_runs_conceded': sum(stats['powerplay_runs_conceded']) / len(stats['powerplay_runs_conceded']) if stats['powerplay_runs_conceded'] else 0,
                'avg_death_over_runs_conceded': sum(stats['death_over_runs_conceded']) / len(stats['death_over_runs_conceded']) if stats['death_over_runs_conceded'] else 0
            }
            
            # Add ball outcome probabilities for Markov chain modeling
            if stats['total_balls_faced'] > 0:
                for runs in range(7):  # 0-6 runs
                    count = 0
                    # Count occurrences of each run outcome for this team
                    for data in data_list:
                        for inning in data.get('innings', []):
                            if inning.get('team') == team:  # Only count when this team is batting
                                for over in inning.get('overs', []):
                                    for delivery in over.get('deliveries', []):
                                        if 'extras' not in delivery or not any(k in delivery['extras'] for k in ['wides', 'noballs']):
                                            if delivery['runs']['batter'] == runs:
                                                count += 1
                    team_summary[team][f'runs_{runs}_probability'] = (count / stats['total_balls_faced']) * 100 if stats['total_balls_faced'] > 0 else 0
    
    return team_summary

def calculate_markov_chain_stats(data_list, team_wise=False):
    """
    Calculate statistical summaries useful for Markov chain cricket simulation.
    
    Args:
        data_list: List of cricket match data (JSON format)
    
    Returns:
        dict: Statistical summaries including runs per ball, run rates, and percentages
    """
    all_deliveries = []
    
    # New counters for detailed over-level boundary stats
    fours_in_over_counts = {0: 0, 1: 0, 2: 0, '3+': 0}
    sixes_in_over_counts = {0: 0, 1: 0, 2: 0, '3+': 0}
    both_in_over_counts = {0: 0, 1: 0, 2: 0, '3+': 0} # Combined fours and sixes
    total_overs = 0

    # Extract all deliveries from all matches
    for data in data_list:
        for inning in data.get('innings', []):
            inning_team = inning.get('team', 'Unknown')
            for over in inning.get('overs', []):
                total_overs += 1
                over_num = over.get('over', 0)
                fours_this_over = 0
                sixes_this_over = 0
                
                for ball_num, delivery in enumerate(over.get('deliveries', [])):
                    # Skip extras (wides, no-balls) for ball-by-ball analysis
                    if 'extras' not in delivery or not any(k in delivery['extras'] for k in ['wides', 'noballs']):
                        is_four = delivery['runs']['batter'] == 4
                        is_six = delivery['runs']['batter'] == 6
                        if is_four:
                            fours_this_over += 1
                        if is_six:
                            sixes_this_over += 1

                        delivery_info = {
                            'team': inning_team,
                            'over': over_num,
                            'ball': ball_num + 1,
                            'runs_off_bat': delivery['runs']['batter'],
                            'total_runs': delivery['runs']['total'],
                            'extras': delivery['runs']['extras'],
                            'is_wicket': 'wickets' in delivery,
                            'is_four': is_four,
                            'is_six': is_six,
                            'is_dot': delivery['runs']['total'] == 0,
                            'is_single': delivery['runs']['batter'] == 1,
                            'phase': 'powerplay' if over_num < 6 else 'middle' if over_num < 15 else 'death'
                        }
                        all_deliveries.append(delivery_info)
                
                # Categorize and count for fours
                if fours_this_over == 0: fours_in_over_counts[0] += 1
                elif fours_this_over == 1: fours_in_over_counts[1] += 1
                elif fours_this_over == 2: fours_in_over_counts[2] += 1
                else: fours_in_over_counts['3+'] += 1

                # Categorize and count for sixes
                if sixes_this_over == 0: sixes_in_over_counts[0] += 1
                elif sixes_this_over == 1: sixes_in_over_counts[1] += 1
                elif sixes_this_over == 2: sixes_in_over_counts[2] += 1
                else: sixes_in_over_counts['3+'] += 1
                
                # Categorize and count for combined boundaries
                both_this_over = fours_this_over + sixes_this_over
                if both_this_over == 0: both_in_over_counts[0] += 1
                elif both_this_over == 1: both_in_over_counts[1] += 1
                elif both_this_over == 2: both_in_over_counts[2] += 1
                else: both_in_over_counts['3+'] += 1

    if not all_deliveries:
        return {"error": "No valid deliveries found in the data"}
    
    total_balls = len(all_deliveries)
    
    # Calculate basic statistics
    stats = {
        'total_balls_analyzed': total_balls,
        'total_matches': len(data_list),
        
        # Runs per ball statistics
        'avg_runs_per_ball': sum(d['runs_off_bat'] for d in all_deliveries) / total_balls,
        'avg_total_runs_per_ball': sum(d['total_runs'] for d in all_deliveries) / total_balls,
        
        # Run rate (runs per over)
        'avg_run_rate': (sum(d['runs_off_bat'] for d in all_deliveries) / total_balls) * 6,
        'avg_total_run_rate': (sum(d['total_runs'] for d in all_deliveries) / total_balls) * 6,
        
        # Ball outcome percentages
        'dot_ball_percentage': (sum(1 for d in all_deliveries if d['is_dot']) / total_balls) * 100,
        'single_percentage': (sum(1 for d in all_deliveries if d['is_single']) / total_balls) * 100,
        'four_percentage': (sum(1 for d in all_deliveries if d['is_four']) / total_balls) * 100,
        'six_percentage': (sum(1 for d in all_deliveries if d['is_six']) / total_balls) * 100,
        'wicket_percentage': (sum(1 for d in all_deliveries if d['is_wicket']) / total_balls) * 100,
        
        # Phase-wise statistics (useful for Markov states)
        'powerplay_stats': {},
        'middle_overs_stats': {},
        'death_overs_stats': {},
        
        # Over-level boundary stats (percentages)
        'total_overs': total_overs,
        'fours_in_over_percentages': {k: (v / total_overs) * 100 if total_overs > 0 else 0 for k, v in fours_in_over_counts.items()},
        'sixes_in_over_percentages': {k: (v / total_overs) * 100 if total_overs > 0 else 0 for k, v in sixes_in_over_counts.items()},
        'both_in_over_percentages': {k: (v / total_overs) * 100 if total_overs > 0 else 0 for k, v in both_in_over_counts.items()},
    }
    
    # Calculate phase-wise statistics
    for phase in ['powerplay', 'middle', 'death']:
        phase_deliveries = [d for d in all_deliveries if d['phase'] == phase]
        if phase_deliveries:
            phase_balls = len(phase_deliveries)
            phase_stats = {
                'balls': phase_balls,
                'avg_runs_per_ball': sum(d['runs_off_bat'] for d in phase_deliveries) / phase_balls,
                'run_rate': (sum(d['runs_off_bat'] for d in phase_deliveries) / phase_balls) * 6,
                'dot_ball_percentage': (sum(1 for d in phase_deliveries if d['is_dot']) / phase_balls) * 100,
                'single_percentage': (sum(1 for d in phase_deliveries if d['is_single']) / phase_balls) * 100,
                'four_percentage': (sum(1 for d in phase_deliveries if d['is_four']) / phase_balls) * 100,
                'six_percentage': (sum(1 for d in phase_deliveries if d['is_six']) / phase_balls) * 100,
                'wicket_percentage': (sum(1 for d in phase_deliveries if d['is_wicket']) / phase_balls) * 100
            }
            stats[f'{phase}_stats'] = phase_stats
    
    # Transition probabilities for Markov chain (runs scored on current ball)
    runs_distribution = {}
    for runs in range(7):  # 0-6 runs
        count = sum(1 for d in all_deliveries if d['runs_off_bat'] == runs)
        runs_distribution[f'runs_{runs}_probability'] = (count / total_balls) * 100
    
    stats.update(runs_distribution)
    
    # Wicket fall patterns (useful for state transitions)
    wicket_balls = [d for d in all_deliveries if d['is_wicket']]
    if wicket_balls:
        stats['avg_balls_between_wickets'] = total_balls / len(wicket_balls)
    
    # Boundary patterns
    boundary_balls = [d for d in all_deliveries if d['is_four'] or d['is_six']]
    if boundary_balls:
        stats['boundary_percentage'] = (len(boundary_balls) / total_balls) * 100
        stats['avg_balls_between_boundaries'] = total_balls / len(boundary_balls)
    
    # First over and first 6 overs analysis
    first_over_runs = []
    first_6_overs_runs = []
    
    for data in data_list:
        for inning in data.get('innings', []):
            first_over_total = 0
            first_6_overs_total = 0
            
            for over in inning.get('overs', []):
                over_num = over.get('over', 0)
                over_runs = sum(d['runs']['total'] for d in over.get('deliveries', []))
                
                if over_num == 0:  # First over (0-indexed)
                    first_over_total = over_runs
                    first_over_runs.append(over_runs)
                
                if over_num < 6:  # First 6 overs (powerplay)
                    first_6_overs_total += over_runs
            
            if first_6_overs_total > 0:
                first_6_overs_runs.append(first_6_overs_total)
    
    # Calculate first over and first 6 overs statistics
    if first_over_runs:
        stats['avg_first_over_runs'] = sum(first_over_runs) / len(first_over_runs)
        stats['max_first_over_runs'] = max(first_over_runs)
        stats['min_first_over_runs'] = min(first_over_runs)
        stats['first_over_run_rate'] = stats['avg_first_over_runs']  # Already per over
    
    if first_6_overs_runs:
        stats['avg_first_6_overs_runs'] = sum(first_6_overs_runs) / len(first_6_overs_runs)
        stats['max_first_6_overs_runs'] = max(first_6_overs_runs)
        stats['min_first_6_overs_runs'] = min(first_6_overs_runs)
        stats['first_6_overs_run_rate'] = stats['avg_first_6_overs_runs'] / 6  # Per over rate
    
    # If team-wise analysis is requested, add team-specific statistics
    if team_wise:
        unique_teams = list(set(d['team'] for d in all_deliveries))
        stats['teams_analyzed'] = unique_teams
        stats['team_stats'] = {}
        
        for team in unique_teams:
            team_data = calculate_team_stats(all_deliveries, team)
            if team_data:
                stats['team_stats'][team] = team_data
    
    return stats

def to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def get_player_summaries_single_match(data):
    """Creates DataFrames for player batting and bowling summaries for a single match."""
    info = data.get('info', {})
    player_stats = {p: {'team': t, 'runs': 0, 'balls_faced': 0, 'fours': 0, 'sixes': 0, 'runs_conceded': 0, 'balls_bowled': 0, 'wickets': 0} for t, ps in info.get('players', {}).items() for p in ps}

    for inning in data.get('innings', []):
        for over in inning.get('overs', []):
            for delivery in over.get('deliveries', []):
                batter, bowler = delivery.get('batter'), delivery.get('bowler')
                
                if batter in player_stats:
                    player_stats[batter]['runs'] += delivery['runs']['batter']
                    player_stats[batter]['balls_faced'] += 1
                    if delivery['runs']['batter'] == 4: player_stats[batter]['fours'] += 1
                    if delivery['runs']['batter'] == 6: player_stats[batter]['sixes'] += 1
                
                if bowler in player_stats:
                    player_stats[bowler]['runs_conceded'] += delivery['runs']['total']
                    player_stats[bowler]['balls_bowled'] += 1
                    if 'wickets' in delivery: player_stats[bowler]['wickets'] += 1

    batting_records = [{'player_name': p, **s} for p, s in player_stats.items() if s['balls_faced'] > 0]
    bowling_records = [{'player_name': p, **s} for p, s in player_stats.items() if s['balls_bowled'] > 0]
    
    batting_df = pd.DataFrame(batting_records)
    bowling_df = pd.DataFrame(bowling_records)
    
    if not batting_df.empty:
        batting_df['strike_rate'] = (batting_df['runs'] / batting_df['balls_faced'].replace(0, 1) * 100).round(2)
    if not bowling_df.empty:
        bowling_df['overs'] = bowling_df['balls_bowled'].apply(lambda x: f"{int(x // 6)}.{int(x % 6)}")
        bowling_df['economy_rate'] = (bowling_df['runs_conceded'] / (bowling_df['balls_bowled'].replace(0, 1) / 6)).round(2)

    return batting_df.sort_values('runs', ascending=False), bowling_df.sort_values('wickets', ascending=False)

def get_betting_market_summary_dict(data):
    """Generates a dictionary of betting market outcomes for a single match with standardized keys."""
    info = data.get('info', {})
    innings = data.get('innings', [])
    batting_df, bowling_df = get_player_summaries_single_match(data)
    
    winner = info.get('outcome', {}).get('winner', 'No Result')

    inning_stats = []
    four_and_six_in_over = "No"
    overs_with_wicket = 0
    for i, inning_data in enumerate(innings):
        stats = {'team': inning_data.get('team', f'Innings {i+1}'),'total_runs': 0,'powerplay_runs': 0,'runs_overs_7_13': 0, 'runs_overs_14_20': 0, 'highest_over': 0,'fall_of_1st_wicket': 'N/A', 'runs_per_over': [], 'first_over_runs': 0, 'first_6_overs_runs': 0, 'fours': 0, 'sixes': 0, 'wickets': 0, 'wides': 0}
        running_score = 0
        wicket_fell = False
        for over in inning_data.get('overs', []):
            over_num = over.get('over', -1)
            over_runs = sum(d['runs']['total'] for d in over.get('deliveries', []))
            
            stats['runs_per_over'].append(over_runs)
            if over_runs > stats['highest_over']: stats['highest_over'] = over_runs
            
            if over_num < 6: 
                stats['powerplay_runs'] += over_runs
                stats['first_6_overs_runs'] += over_runs
            if over_num == 0:  # First over (0-indexed)
                stats['first_over_runs'] = over_runs
            if 6 <= over_num <= 12: stats['runs_overs_7_13'] += over_runs
            if 13 <= over_num <= 19: stats['runs_overs_14_20'] += over_runs

            has_four = any(d['runs']['batter'] == 4 for d in over.get('deliveries', []))
            has_six = any(d['runs']['batter'] == 6 for d in over.get('deliveries', []))
            if has_four and has_six: four_and_six_in_over = "Yes"
            if any('wickets' in d for d in over.get('deliveries', [])): overs_with_wicket += 1
                
            # Count deliveries in this over for detailed stats
            for delivery in over.get('deliveries', []):
                runs = delivery['runs']['batter']
                total_runs = delivery['runs']['total']
                
                # Count fours and sixes
                if runs == 4:
                    stats['fours'] += 1
                elif runs == 6:
                    stats['sixes'] += 1
                
                # Count wickets
                if 'wickets' in delivery:
                    stats['wickets'] += 1
                
                # Count wides
                if 'extras' in delivery and 'wides' in delivery['extras']:
                    stats['wides'] += delivery['extras']['wides']
                
                # Track fall of first wicket
                if not wicket_fell:
                    running_score += total_runs
                    if 'wickets' in delivery:
                        stats['fall_of_1st_wicket'] = running_score
                        wicket_fell = True
        stats['total_runs'] = sum(d['runs']['total'] for o in inning_data.get('overs', []) for d in o.get('deliveries', []))
        inning_stats.append(stats)
        
    summary_dict = {
        'match_id': data.get('match_id', 'N/A'),
        'Match Winner': winner,
        'Tied Match': 'Yes' if info.get('outcome', {}).get('result') == 'tie' else 'No',
        'Innings 1 Team': inning_stats[0]['team'] if len(inning_stats) > 0 else 'N/A',
        'Innings 1 Runs': inning_stats[0]['total_runs'] if len(inning_stats) > 0 else 0,
        'Innings 1 First Over Runs': inning_stats[0]['first_over_runs'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs (Overs 1-6)': inning_stats[0]['powerplay_runs'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs (Overs 7-13)': inning_stats[0]['runs_overs_7_13'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs (Overs 14-20)': inning_stats[0]['runs_overs_14_20'] if len(inning_stats) > 0 else 0,
        'Innings 2 Team': inning_stats[1]['team'] if len(inning_stats) > 1 else 'N/A',
        'Innings 2 Runs': inning_stats[1]['total_runs'] if len(inning_stats) > 1 else 0,
        'Innings 2 First Over Runs': inning_stats[1]['first_over_runs'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs (Overs 1-6)': inning_stats[1]['powerplay_runs'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs (Overs 7-13)': inning_stats[1]['runs_overs_7_13'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs (Overs 14-20)': inning_stats[1]['runs_overs_14_20'] if len(inning_stats) > 1 else 0,
        'Top Batsman Match': batting_df.iloc[0]['player_name'] if not batting_df.empty else 'N/A',
        'Top Batsman Runs': batting_df.iloc[0]['runs'] if not batting_df.empty else 'N/A',
        'Man of the Match': info.get('player_of_match', ['N/A'])[0],
        'Toss Winner': info.get('toss', {}).get('winner', 'N/A'),
        'Four and Six in an Over': four_and_six_in_over,
        'Overs with a Wicket': overs_with_wicket,
        
        # Additional betting market statistics
        'Max Over in Match': max([inning_stats[i]['highest_over'] for i in range(len(inning_stats))]) if inning_stats else 0,
        'Match Fours': sum([inning_stats[i]['fours'] for i in range(len(inning_stats))]) if inning_stats else 0,
        'Match Sixes': sum([inning_stats[i]['sixes'] for i in range(len(inning_stats))]) if inning_stats else 0,
        'Match Wickets': sum([inning_stats[i]['wickets'] for i in range(len(inning_stats))]) if inning_stats else 0,
        'Match Wides': sum([inning_stats[i]['wides'] for i in range(len(inning_stats))]) if inning_stats else 0,
        
        # Innings 1 detailed statistics
        'Innings 1 Fours': inning_stats[0]['fours'] if len(inning_stats) > 0 else 0,
        'Innings 1 Sixes': inning_stats[0]['sixes'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs at Fall of 1st Wicket': inning_stats[0]['fall_of_1st_wicket'] if len(inning_stats) > 0 else 'N/A',
        'Innings 1 Highest Over': inning_stats[0]['highest_over'] if len(inning_stats) > 0 else 0,
        'Innings 1 Wickets': inning_stats[0]['wickets'] if len(inning_stats) > 0 else 0,
        
        # Innings 2 detailed statistics
        'Innings 2 Fours': inning_stats[1]['fours'] if len(inning_stats) > 1 else 0,
        'Innings 2 Sixes': inning_stats[1]['sixes'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs at Fall of 1st Wicket': inning_stats[1]['fall_of_1st_wicket'] if len(inning_stats) > 1 else 'N/A',
        'Innings 2 Highest Over': inning_stats[1]['highest_over'] if len(inning_stats) > 1 else 0,
        'Innings 2 Wickets': inning_stats[1]['wickets'] if len(inning_stats) > 1 else 0
    }
    return summary_dict

# --- Main Data Processing Function ---

@st.cache_data
def process_all_files(uploaded_files):
    """Processes a list of uploaded JSON files and aggregates all data."""
    all_match_data, all_market_summaries, all_match_summaries, all_ball_by_ball, all_batting, all_bowling = [], [], [], [], [], []

    for uploaded_file in uploaded_files:
        try:
            data = json.loads(uploaded_file.getvalue())
            match_id = uploaded_file.name
            data['match_id'] = match_id
            
            all_match_data.append(data)
            all_market_summaries.append(get_betting_market_summary_dict(data))
            
            info, innings = data.get('info', {}), data.get('innings', [])
            home_team, away_team = info.get('teams', ['N/A', 'N/A'])[:2]
            winner = info.get('outcome', {}).get('winner', 'No Result')

            home_score = sum(d['runs']['total'] for o in innings[0]['overs'] for d in o['deliveries']) if len(innings) > 0 else 0
            away_score = sum(d['runs']['total'] for o in innings[1]['overs'] for d in o['deliveries']) if len(innings) > 1 else 0
            all_match_summaries.append({'match_id': match_id, 'date': info.get('dates', ['N/A'])[0], 'home_team': home_team, 'away_team': away_team,'toss_winner': info.get('toss', {}).get('winner', 'N/A'), 'toss_decision': info.get('toss', {}).get('decision', 'N/A'),'winner': winner, 'home_score': home_score, 'away_score': away_score, 'venue': info.get('venue', 'N/A')})
            
            for i, inning in enumerate(innings):
                for over in inning.get('overs', []):
                    for j, delivery in enumerate(over.get('deliveries', [])):
                        all_ball_by_ball.append({'match_id': match_id, 'inning': i + 1, 'over': over['over'] + 1, 'ball': j + 1, 'batting_team': inning['team'], 'batter': delivery['batter'], 'bowler': delivery['bowler'], 'runs_off_bat': delivery['runs']['batter'], 'extras': delivery['runs']['extras'], 'total_runs': delivery['runs']['total']})

            bat_df, bowl_df = get_player_summaries_single_match(data)
            all_batting.append(bat_df)
            all_bowling.append(bowl_df)

        except Exception as e:
            st.error(f"Error processing file {uploaded_file.name}: {e}")
            continue

    match_summary_df = pd.DataFrame(all_match_summaries)
    ball_by_ball_df = pd.DataFrame(all_ball_by_ball)
    market_summaries_df = pd.DataFrame(all_market_summaries)
    
    agg_batting, agg_bowling = pd.DataFrame(), pd.DataFrame()
    if all_batting:
        full_batting_df = pd.concat(all_batting)
        if not full_batting_df.empty:
            agg_batting = full_batting_df.groupby(['player_name', 'team'])[['runs', 'balls_faced', 'fours', 'sixes']].sum().reset_index()
            agg_batting['strike_rate'] = (agg_batting['runs'] / agg_batting['balls_faced'].replace(0, 1) * 100).round(2)

    if all_bowling:
        full_bowling_df = pd.concat(all_bowling)
        if not full_bowling_df.empty:
            agg_bowling = full_bowling_df.groupby(['player_name', 'team'])[['runs_conceded', 'balls_bowled', 'wickets']].sum().reset_index()
            agg_bowling['overs'] = agg_bowling['balls_bowled'].apply(lambda x: f"{int(x // 6)}.{int(x % 6)}")
            agg_bowling['economy_rate'] = (agg_bowling['runs_conceded'] / (agg_bowling['balls_bowled'].replace(0, 1) / 6)).round(2)

    return all_match_data, match_summary_df, ball_by_ball_df, agg_batting.sort_values('runs', ascending=False), agg_bowling.sort_values('wickets', ascending=False), market_summaries_df

# --- CSV Analyzer Functions ---
def display_toss_analysis(df):
    st.subheader("Toss Analysis")
    if 'Toss Winner' in df.columns and 'Match Winner' in df.columns:
        toss_winner_match_winner = df[df['Toss Winner'] == df['Match Winner']]
        toss_win_rate = (len(toss_winner_match_winner) / len(df)) * 100 if len(df) > 0 else 0
        
        st.metric("Toss Winner Wins Match %", f"{toss_win_rate:.2f}%")
        
        if not toss_winner_match_winner.empty and 'toss_decision' in toss_winner_match_winner.columns:
            st.write("**Winning Toss Decision Breakdown:**")
            fig = px.pie(toss_winner_match_winner, names='toss_decision', title='Decision of Toss Winners Who Also Won the Match')
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Toss Winner or Match Winner columns not found in the uploaded CSV.")

def display_frequency_analysis(df):
    st.subheader("Frequency Analysis")
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
    if categorical_cols:
        col_to_analyze = st.selectbox("Select a column to analyze", categorical_cols)
        if col_to_analyze:
            counts = df[col_to_analyze].value_counts().reset_index()
            counts.columns = [col_to_analyze, 'count']
            
            fig = px.bar(counts, x=col_to_analyze, y='count', title=f"Frequency of each category in {col_to_analyze}")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(counts)
    else:
        st.info("No categorical columns found for frequency analysis.")

# --- Main App UI ---
st.title("🏏 Multi-Match Cricket Data Analyzer")

# Initialize session state
if 'json_files' not in st.session_state:
    st.session_state.json_files = None

st.sidebar.header("Upload Data")
st.session_state.json_files = st.sidebar.file_uploader("Upload JSON match files", type=["json"], accept_multiple_files=True)

if st.sidebar.button("Clear Uploaded Files"):
    st.session_state.json_files = None
    st.experimental_rerun()

st.sidebar.header("Navigation")
# Always show JSON analyzer. Show CSV analyzer only if JSONs are uploaded.
nav_options = ["JSON Data Analyzer"]
if st.session_state.json_files:
    nav_options.append("CSV Market Analyzer")
page = st.sidebar.radio("Choose an analyzer", nav_options)


if page == "JSON Data Analyzer":
    if st.session_state.json_files:
        raw_data, match_summary, bbb, batting_summary, bowling_summary, market_summaries_df = process_all_files(st.session_state.json_files)
        
        # Calculate comprehensive betting markets
        if BETTING_MARKETS_AVAILABLE:
            betting_markets = calculate_betting_markets(raw_data)
            formatted_betting_markets = format_betting_markets_for_display(betting_markets)
        else:
            betting_markets = {}
            formatted_betting_markets = {}

        st.sidebar.subheader("JSON Analyzer Views")
        json_page = st.sidebar.radio("Choose a data view", ["Match Summaries", "Aggregated Batting Stats", "Aggregated Bowling Stats", "Combined Ball-by-Ball", "Betting Market Summaries", "Markov Chain Statistics", "Venue-wise Statistics", "Team-wise Statistics"])
        
        st.header(f"Analysis of {len(st.session_state.json_files)} Match(es)")
        st.markdown("---")

        if json_page == "Match Summaries":
            st.subheader("Match Summaries (Standardized)")
            st.dataframe(match_summary)
            if st.button("Copy Summaries to Clipboard"):
                st.text_area("Copy this text", match_summary.to_csv(index=False), height=200)
            st.download_button("Download Summaries CSV", to_csv(match_summary), "match_summaries.csv", "text/csv")
        
        elif json_page == "Aggregated Batting Stats":
            st.subheader("Aggregated Player Batting Stats")
            st.dataframe(batting_summary)
            if st.button("Copy Batting Stats to Clipboard"):
                st.text_area("Copy this text", batting_summary.to_csv(index=False), height=200)
            st.download_button("Download Batting CSV", to_csv(batting_summary), "aggregated_batting_summary.csv", "text/csv")
        
        elif json_page == "Aggregated Bowling Stats":
            st.subheader("Aggregated Player Bowling Stats")
            st.dataframe(bowling_summary)
            if st.button("Copy Bowling Stats to Clipboard"):
                st.text_area("Copy this text", bowling_summary.to_csv(index=False), height=200)
            st.download_button("Download Bowling CSV", to_csv(bowling_summary), "aggregated_bowling_summary.csv", "text/csv")
        
        elif json_page == "Combined Ball-by-Ball":
            st.subheader("Combined Ball-by-Ball Data")
            st.dataframe(bbb)
            if st.button("Copy Ball-by-Ball Data to Clipboard"):
                st.text_area("Copy this text", bbb.to_csv(index=False), height=200)
            st.download_button("Download Ball-by-Ball CSV", to_csv(bbb), "combined_ball_by_ball.csv", "text/csv")
        
        elif json_page == "Betting Market Summaries":
            st.subheader("🎯 Comprehensive Betting Markets Analysis")
            
            if not BETTING_MARKETS_AVAILABLE:
                st.error("❌ Betting Markets module is not available.")
                if betting_markets_error:
                    st.error(f"Error details: {betting_markets_error}")
                st.info("📋 The betting markets functionality requires the betting_markets.py module to be properly imported. Please check the file and dependencies.")
                st.info("💡 You can still use all other features of the cricket analyzer (Match Summaries, Player Stats, Ball-by-Ball Data, Markov Chain Statistics, etc.)")
            elif formatted_betting_markets:
                # Create tabs for different market categories
                market_tabs = st.tabs([
                    "Match Outcomes", "Runs Markets", "Team Markets", 
                    "Individual Performance", "Phase Markets", "Special Markets",
                    "Wicket Markets", "Partnership Markets"
                ])
                
                with market_tabs[0]:  # Match Outcomes
                    st.subheader("Match Outcome Markets")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Match Winner**")
                        match_winner = formatted_betting_markets['Match Outcome Markets']['Match Winner']
                        for outcome, data in match_winner.items():
                            if isinstance(data, dict) and 'count' in data and 'percentage' in data:
                                st.metric(outcome.replace('_', ' ').title(), f"{data['count']} ({data['percentage']}%)")
                            else:
                                st.metric(outcome.replace('_', ' ').title(), data)
                        
                        st.write("**Most Sixes**")
                        most_sixes = formatted_betting_markets['Match Outcome Markets']['Most Sixes']
                        for outcome, data in most_sixes.items():
                            if isinstance(data, dict) and 'count' in data and 'percentage' in data:
                                st.metric(outcome.replace('_', ' ').title(), f"{data['count']} ({data['percentage']}%)")
                            else:
                                st.metric(outcome.replace('_', ' ').title(), data)
                    
                    with col2:
                        st.write("**Toss Winner**")
                        toss_winner = formatted_betting_markets['Match Outcome Markets']['Toss Winner']
                        for outcome, data in toss_winner.items():
                            if isinstance(data, dict) and 'count' in data and 'percentage' in data:
                                st.metric(outcome.replace('_', ' ').title(), f"{data['count']} ({data['percentage']}%)")
                            else:
                                st.metric(outcome.replace('_', ' ').title(), data)
                        
                        st.write("**Most Fours**")
                        most_fours = formatted_betting_markets['Match Outcome Markets']['Most Fours']
                        for outcome, data in most_fours.items():
                            if isinstance(data, dict) and 'count' in data and 'percentage' in data:
                                st.metric(outcome.replace('_', ' ').title(), f"{data['count']} ({data['percentage']}%)")
                            else:
                                st.metric(outcome.replace('_', ' ').title(), data)
                
                with market_tabs[1]:  # Runs Markets
                    st.subheader("Runs Markets - Interactive Over/Under Analysis")
                    
                    runs_markets = formatted_betting_markets['Runs Markets']
                    
                    for market_name, market_data in runs_markets.items():
                        if isinstance(market_data, dict) and 'Average' in market_data:
                            st.write(f"**{market_name}**")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Average", f"{market_data['Average']:.1f}")
                            with col2:
                                st.metric("Median", market_data['Median'])
                            with col3:
                                st.metric("Min", market_data['Min'])
                            with col4:
                                st.metric("Max", market_data['Max'])
                            
                            # Interactive Over/Under analysis
                            st.write("**Custom Over/Under Analysis:**")
                            
                            # Get the raw data for custom analysis
                            raw_market_data = betting_markets.get(market_name.lower().replace(' ', '_').replace('match_', ''), {})
                            data_key = None
                            for key in ['runs', 'fours', 'sixes', 'boundaries']:
                                if key in raw_market_data and isinstance(raw_market_data[key], list):
                                    data_key = key
                                    break
                            
                            if data_key and raw_market_data[data_key]:
                                data_list = raw_market_data[data_key]
                                
                                # User input for custom line
                                default_line = int(market_data['Average'])
                                custom_line = st.number_input(
                                    f"Enter your over/under line for {market_name}:",
                                    min_value=0,
                                    max_value=int(market_data['Max']) + 50,
                                    value=default_line,
                                    step=1,
                                    key=f"line_{market_name.replace(' ', '_')}"
                                )
                                
                                # Calculate custom over/under
                                custom_result = calculate_custom_over_under(data_list, custom_line)
                                
                                if 'error' not in custom_result:
                                    col_over, col_under = st.columns(2)
                                    with col_over:
                                        st.metric(
                                            f"Over {custom_line}",
                                            f"{custom_result['over_percentage']}%",
                                            f"{custom_result['over_count']} matches"
                                        )
                                    with col_under:
                                        st.metric(
                                            f"Under {custom_line}",
                                            f"{custom_result['under_percentage']}%",
                                            f"{custom_result['under_count']} matches"
                                        )
                                
                                # Show predefined lines as well
                                if 'Over/Under Lines' in market_data and market_data['Over/Under Lines']:
                                    with st.expander("View Predefined Lines"):
                                        over_under_data = []
                                        for line_key, line_data in market_data['Over/Under Lines'].items():
                                            line_value = line_key.replace('line_', '')
                                            over_under_data.append({
                                                'Line': line_value,
                                                'Over %': f"{line_data['over_percentage']:.1f}%",
                                                'Under %': f"{line_data['under_percentage']:.1f}%",
                                                'Over Count': line_data['over_count'],
                                                'Under Count': line_data['under_count']
                                            })
                                        
                                        if over_under_data:
                                            st.dataframe(pd.DataFrame(over_under_data), use_container_width=True)
                            
                            st.markdown("---")
                
                with market_tabs[2]:  # Team Markets
                    st.subheader("Team-Specific Markets")
                    
                    team_markets = formatted_betting_markets['Team Markets']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Home Team Markets**")
                        for market_name, market_data in team_markets.items():
                            if 'Home' in market_name and isinstance(market_data, dict) and 'Average' in market_data:
                                st.write(f"*{market_name}*")
                                subcol1, subcol2 = st.columns(2)
                                with subcol1:
                                    st.metric("Avg", f"{market_data['Average']:.1f}")
                                with subcol2:
                                    st.metric("Range", f"{market_data['Min']}-{market_data['Max']}")
                    
                    with col2:
                        st.write("**Away Team Markets**")
                        for market_name, market_data in team_markets.items():
                            if 'Away' in market_name and isinstance(market_data, dict) and 'Average' in market_data:
                                st.write(f"*{market_name}*")
                                subcol1, subcol2 = st.columns(2)
                                with subcol1:
                                    st.metric("Avg", f"{market_data['Average']:.1f}")
                                with subcol2:
                                    st.metric("Range", f"{market_data['Min']}-{market_data['Max']}")
                
                with market_tabs[3]:  # Individual Performance
                    st.subheader("Individual Performance Markets")
                    
                    individual_markets = formatted_betting_markets['Individual Performance']
                    
                    for market_name, market_data in individual_markets.items():
                        if isinstance(market_data, dict) and 'Average' in market_data:
                            st.write(f"**{market_name}**")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Average", f"{market_data['Average']:.1f}")
                            with col2:
                                st.metric("Median", market_data['Median'])
                            with col3:
                                st.metric("Min", market_data['Min'])
                            with col4:
                                st.metric("Max", market_data['Max'])
                            
                            st.markdown("---")
                
                with market_tabs[4]:  # Phase Markets
                    st.subheader("Phase-wise Runs Markets")
                    st.info("📊 Phase markets analyze runs scored in first 6, 10, and 15 overs of the 1st innings only")
                    
                    phase_markets = formatted_betting_markets['Phase Markets']
                    
                    for market_name, market_data in phase_markets.items():
                        if isinstance(market_data, dict) and 'Average' in market_data:
                            st.write(f"**{market_name}**")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Average", f"{market_data['Average']:.1f}")
                            with col2:
                                st.metric("Median", market_data['Median'])
                            with col3:
                                st.metric("Min", market_data['Min'])
                            with col4:
                                st.metric("Max", market_data['Max'])
                            
                            # Interactive Over/Under analysis for phase markets
                            st.write("**Custom Over/Under Analysis:**")
                            
                            # Get the raw data for custom analysis
                            raw_market_key = market_name.lower().replace(' ', '_').replace('(1st_innings_only)', '').replace('runs_', '').strip()
                            raw_market_data = betting_markets.get(f'runs_{raw_market_key}', {})
                            
                            if 'runs' in raw_market_data and isinstance(raw_market_data['runs'], list):
                                data_list = raw_market_data['runs']
                                
                                # User input for custom line
                                default_line = int(market_data['Average'])
                                custom_line = st.number_input(
                                    f"Enter your over/under line for {market_name}:",
                                    min_value=0,
                                    max_value=int(market_data['Max']) + 20,
                                    value=default_line,
                                    step=1,
                                    key=f"phase_line_{market_name.replace(' ', '_')}"
                                )
                                
                                # Calculate custom over/under
                                custom_result = calculate_custom_over_under(data_list, custom_line)
                                
                                if 'error' not in custom_result:
                                    col_over, col_under = st.columns(2)
                                    with col_over:
                                        st.metric(
                                            f"Over {custom_line}",
                                            f"{custom_result['over_percentage']}%",
                                            f"{custom_result['over_count']} matches"
                                        )
                                    with col_under:
                                        st.metric(
                                            f"Under {custom_line}",
                                            f"{custom_result['under_percentage']}%",
                                            f"{custom_result['under_count']} matches"
                                        )
                            
                            # Show predefined lines as well
                            if 'Over/Under Lines' in market_data and market_data['Over/Under Lines']:
                                with st.expander("View Predefined Lines"):
                                    over_under_data = []
                                    for line_key, line_data in market_data['Over/Under Lines'].items():
                                        line_value = line_key.replace('line_', '')
                                        over_under_data.append({
                                            'Line': line_value,
                                            'Over %': f"{line_data['over_percentage']:.1f}%",
                                            'Under %': f"{line_data['under_percentage']:.1f}%"
                                        })
                                    
                                    if over_under_data:
                                        st.dataframe(pd.DataFrame(over_under_data), use_container_width=True)
                            
                            st.markdown("---")
                
                with market_tabs[5]:  # Special Markets
                    st.subheader("Special Betting Markets")
                    st.info("📊 All special markets now include percentages for better analysis")
                    
                    special_markets = formatted_betting_markets['Special Markets']
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        for i, (market_name, market_data) in enumerate(special_markets.items()):
                            if i % 2 == 0:
                                st.write(f"**{market_name}**")
                                if isinstance(market_data, dict):
                                    for outcome, data in market_data.items():
                                        if isinstance(data, dict) and 'count' in data and 'percentage' in data:
                                            st.metric(
                                                outcome.replace('_', ' ').title(),
                                                f"{data['count']} ({data['percentage']}%)"
                                            )
                                        else:
                                            # Fallback for non-percentage data
                                            st.metric(outcome.replace('_', ' ').title(), data)
                                st.markdown("---")
                    
                    with col2:
                        for i, (market_name, market_data) in enumerate(special_markets.items()):
                            if i % 2 == 1:
                                st.write(f"**{market_name}**")
                                if isinstance(market_data, dict):
                                    for outcome, data in market_data.items():
                                        if isinstance(data, dict) and 'count' in data and 'percentage' in data:
                                            st.metric(
                                                outcome.replace('_', ' ').title(),
                                                f"{data['count']} ({data['percentage']}%)"
                                            )
                                        else:
                                            # Fallback for non-percentage data
                                            st.metric(outcome.replace('_', ' ').title(), data)
                                st.markdown("---")
                
                with market_tabs[6]:  # Wicket Markets
                    st.subheader("Wicket-Related Markets")
                    
                    wicket_markets = formatted_betting_markets['Wicket Markets']
                    
                    for market_name, market_data in wicket_markets.items():
                        if isinstance(market_data, dict) and 'Average' in market_data:
                            st.write(f"**{market_name}**")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Average", f"{market_data['Average']:.1f}")
                            with col2:
                                st.metric("Median", market_data['Median'])
                            with col3:
                                st.metric("Min", market_data['Min'])
                            with col4:
                                st.metric("Max", market_data['Max'])
                            
                            st.markdown("---")
                
                with market_tabs[7]:  # Partnership Markets
                    st.subheader("Partnership Markets")
                    
                    partnership_markets = formatted_betting_markets['Partnership Markets']
                    
                    for market_name, market_data in partnership_markets.items():
                        if isinstance(market_data, dict) and 'Average' in market_data:
                            st.write(f"**{market_name}**")
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.metric("Average", f"{market_data['Average']:.1f}")
                            with col2:
                                st.metric("Median", market_data['Median'])
                            with col3:
                                st.metric("Min", market_data['Min'])
                            with col4:
                                st.metric("Max", market_data['Max'])
                            
                            # Show match outcome analysis for opening partnership
                            if 'Match Outcomes' in market_data:
                                st.write("**Match Outcome Analysis:**")
                                outcome_col1, outcome_col2, outcome_col3 = st.columns(3)
                                
                                with outcome_col1:
                                    st.metric(
                                        "Home Team Wins",
                                        market_data['Match Outcomes']['Home Team Wins']
                                    )
                                with outcome_col2:
                                    st.metric(
                                        "Away Team Wins", 
                                        market_data['Match Outcomes']['Away Team Wins']
                                    )
                                with outcome_col3:
                                    st.metric(
                                        "Ties/No Results",
                                        market_data['Match Outcomes']['Ties/No Results']
                                    )
                                
                                # Show percentages
                                if 'Match Outcome Percentages' in market_data:
                                    st.write("**Match Outcome Percentages:**")
                                    perc_col1, perc_col2, perc_col3 = st.columns(3)
                                    
                                    with perc_col1:
                                        st.metric(
                                            "Home Win %",
                                            f"{market_data['Match Outcome Percentages']['Home Team Win %']}%"
                                        )
                                    with perc_col2:
                                        st.metric(
                                            "Away Win %",
                                            f"{market_data['Match Outcome Percentages']['Away Team Win %']}%"
                                        )
                                    with perc_col3:
                                        st.metric(
                                            "Tie/No Result %",
                                            f"{market_data['Match Outcome Percentages']['Tie/No Result %']}%"
                                        )
                            
                            # Interactive Over/Under analysis for partnership markets
                            st.write("**Custom Over/Under Analysis:**")
                            
                            # Get the raw data for custom analysis
                            raw_market_data = betting_markets.get('highest_opening_partnership', {})
                            
                            if 'partnerships' in raw_market_data and isinstance(raw_market_data['partnerships'], list):
                                data_list = raw_market_data['partnerships']
                                
                                # User input for custom line
                                default_line = int(market_data['Average'])
                                custom_line = st.number_input(
                                    f"Enter your over/under line for {market_name}:",
                                    min_value=0,
                                    max_value=int(market_data['Max']) + 20,
                                    value=default_line,
                                    step=1,
                                    key=f"partnership_line_{market_name.replace(' ', '_')}"
                                )
                                
                                # Calculate custom over/under
                                custom_result = calculate_custom_over_under(data_list, custom_line)
                                
                                if 'error' not in custom_result:
                                    col_over, col_under = st.columns(2)
                                    with col_over:
                                        st.metric(
                                            f"Over {custom_line}",
                                            f"{custom_result['over_percentage']}%",
                                            f"{custom_result['over_count']} matches"
                                        )
                                    with col_under:
                                        st.metric(
                                            f"Under {custom_line}",
                                            f"{custom_result['under_percentage']}%",
                                            f"{custom_result['under_count']} matches"
                                        )
                            
                            # Show predefined lines as well
                            if 'Over/Under Lines' in market_data and market_data['Over/Under Lines']:
                                with st.expander("View Predefined Lines"):
                                    over_under_data = []
                                    for line_key, line_data in market_data['Over/Under Lines'].items():
                                        line_value = line_key.replace('line_', '')
                                        over_under_data.append({
                                            'Line': line_value,
                                            'Over %': f"{line_data['over_percentage']:.1f}%",
                                            'Under %': f"{line_data['under_percentage']:.1f}%"
                                        })
                                    
                                    if over_under_data:
                                        st.dataframe(pd.DataFrame(over_under_data), use_container_width=True)
                            
                            st.markdown("---")
                
                # Export section
                st.markdown("---")
                st.subheader("📊 Export Betting Markets Data")
                
                # Create comprehensive export data
                export_data = []
                for category, markets in formatted_betting_markets.items():
                    for market_name, market_data in markets.items():
                        if isinstance(market_data, dict):
                            if 'Average' in market_data:
                                # Numeric market
                                export_data.append({
                                    'Category': category,
                                    'Market': market_name,
                                    'Type': 'Numeric',
                                    'Average': market_data['Average'],
                                    'Median': market_data['Median'],
                                    'Min': market_data['Min'],
                                    'Max': market_data['Max'],
                                    'Sample_Size': market_data['Sample Size']
                                })
                            else:
                                # Categorical market
                                for outcome, count in market_data.items():
                                    export_data.append({
                                        'Category': category,
                                        'Market': market_name,
                                        'Type': 'Categorical',
                                        'Outcome': outcome,
                                        'Count': count,
                                        'Average': None,
                                        'Median': None,
                                        'Min': None,
                                        'Max': None,
                                        'Sample_Size': None
                                    })
                
                if export_data:
                    export_df = pd.DataFrame(export_data)
                    st.download_button(
                        label="📥 Download Complete Betting Markets Analysis",
                        data=to_csv(export_df),
                        file_name="comprehensive_betting_markets.csv",
                        mime="text/csv"
                    )
                
                # Legacy export for compatibility
                if not market_summaries_df.empty:
                    st.download_button(
                        label="📥 Download Legacy Market Summaries",
                        data=to_csv(market_summaries_df),
                        file_name="legacy_market_summaries.csv",
                        mime="text/csv"
                    )
            
            else:
                st.warning("Could not generate betting market analysis from the uploaded files.")
                st.info("Please ensure your JSON files contain valid cricket match data with innings information.")
        
        elif json_page == "Markov Chain Statistics":
            st.subheader("Markov Chain Statistics for Cricket Simulation")
            st.info("These statistics are designed for building Markov chain models to simulate cricket matches.")
            
            # Add option for team-wise analysis
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write("**Analysis Type:**")
            with col2:
                team_wise_analysis = st.checkbox("Team-wise Analysis", value=False, help="Calculate separate statistics for each team")
            
            # Calculate Markov chain statistics
            markov_stats = calculate_markov_chain_stats(raw_data, team_wise=team_wise_analysis)
            
            if "error" in markov_stats:
                st.error(markov_stats["error"])
            else:
                # Display overall statistics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Balls Analyzed", f"{markov_stats['total_balls_analyzed']:,}")
                    st.metric("Total Matches", markov_stats['total_matches'])
                with col2:
                    st.metric("Avg Runs per Ball", f"{markov_stats['avg_runs_per_ball']:.3f}")
                    st.metric("Avg Run Rate", f"{markov_stats['avg_run_rate']:.2f}")
                with col3:
                    st.metric("Dot Ball %", f"{markov_stats['dot_ball_percentage']:.1f}%")
                    st.metric("Boundary %", f"{markov_stats.get('boundary_percentage', 0):.1f}%")

                # Over-level boundary distribution
                st.markdown("---")
                st.subheader("Over-level Boundary Distribution")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("**Fours per Over**")
                    for count, perc in markov_stats['fours_in_over_percentages'].items():
                        st.metric(f"{count} Fours", f"{perc:.1f}%")
                with col2:
                    st.write("**Sixes per Over**")
                    for count, perc in markov_stats['sixes_in_over_percentages'].items():
                        st.metric(f"{count} Sixes", f"{perc:.1f}%")
                with col3:
                    st.write("**Boundaries per Over**")
                    for count, perc in markov_stats['both_in_over_percentages'].items():
                        st.metric(f"{count} Boundaries", f"{perc:.1f}%")

                # First over and first 6 overs statistics
                st.markdown("---")
                st.subheader("First Over & Powerplay Analysis")
                
                first_over_col1, first_over_col2, first_over_col3, first_over_col4 = st.columns(4)
                with first_over_col1:
                    if 'avg_first_over_runs' in markov_stats:
                        st.metric("Avg First Over Runs", f"{markov_stats['avg_first_over_runs']:.1f}")
                with first_over_col2:
                    if 'max_first_over_runs' in markov_stats:
                        st.metric("Max First Over Runs", f"{markov_stats['max_first_over_runs']}")
                with first_over_col3:
                    if 'avg_first_6_overs_runs' in markov_stats:
                        st.metric("Avg First 6 Overs", f"{markov_stats['avg_first_6_overs_runs']:.1f}")
                with first_over_col4:
                    if 'first_6_overs_run_rate' in markov_stats:
                        st.metric("First 6 Overs Rate", f"{markov_stats['first_6_overs_run_rate']:.2f}")
                
                st.markdown("---")
                
                # Ball outcome probabilities
                st.subheader("Ball Outcome Probabilities (for Markov States)")
                prob_cols = st.columns(4)
                for i in range(7):
                    col_idx = i % 4
                    prob_cols[col_idx].metric(f"{i} Runs", f"{markov_stats[f'runs_{i}_probability']:.2f}%")
                
                # Create visualization for runs distribution
                runs_data = []
                for i in range(7):
                    runs_data.append({
                        'Runs': str(i),
                        'Probability': markov_stats[f'runs_{i}_probability']
                    })
                
                runs_df = pd.DataFrame(runs_data)
                fig_runs = px.bar(runs_df, x='Runs', y='Probability', 
                                title='Probability Distribution of Runs per Ball',
                                labels={'Probability': 'Probability (%)'})
                st.plotly_chart(fig_runs, use_container_width=True)
                
                st.markdown("---")
                
                # Phase-wise statistics
                st.subheader("Phase-wise Statistics")
                phases = ['powerplay', 'middle', 'death']
                phase_names = ['Powerplay (Overs 1-6)', 'Middle Overs (7-15)', 'Death Overs (16-20)']
                
                for phase, phase_name in zip(phases, phase_names):
                    if f'{phase}_stats' in markov_stats and markov_stats[f'{phase}_stats']:
                        with st.expander(f"📊 {phase_name}"):
                            phase_data = markov_stats[f'{phase}_stats']
                            
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Balls", f"{phase_data['balls']:,}")
                            col2.metric("Run Rate", f"{phase_data['run_rate']:.2f}")
                            col3.metric("Dot Ball %", f"{phase_data['dot_ball_percentage']:.1f}%")
                            col4.metric("Wicket %", f"{phase_data['wicket_percentage']:.2f}%")
                            
                            # Phase-wise outcome percentages
                            st.write("**Ball Outcome Distribution:**")
                            outcome_cols = st.columns(5)
                            outcome_cols[0].metric("Singles", f"{phase_data['single_percentage']:.1f}%")
                            outcome_cols[1].metric("Fours", f"{phase_data['four_percentage']:.1f}%")
                            outcome_cols[2].metric("Sixes", f"{phase_data['six_percentage']:.1f}%")
                            outcome_cols[3].metric("Dots", f"{phase_data['dot_ball_percentage']:.1f}%")
                            outcome_cols[4].metric("Wickets", f"{phase_data['wicket_percentage']:.2f}%")
                
                st.markdown("---")
                
                # Additional Markov chain insights
                st.subheader("Additional Simulation Parameters")
                col1, col2 = st.columns(2)
                
                with col1:
                    if 'avg_balls_between_wickets' in markov_stats:
                        st.metric("Avg Balls Between Wickets", f"{markov_stats['avg_balls_between_wickets']:.1f}")
                    st.metric("Overall Wicket %", f"{markov_stats['wicket_percentage']:.2f}%")
                
                with col2:
                    if 'avg_balls_between_boundaries' in markov_stats:
                        st.metric("Avg Balls Between Boundaries", f"{markov_stats['avg_balls_between_boundaries']:.1f}")
                    st.metric("Four %", f"{markov_stats['four_percentage']:.2f}%")
                    st.metric("Six %", f"{markov_stats['six_percentage']:.2f}%")
                
                # Team-wise analysis section
                if team_wise_analysis and 'team_stats' in markov_stats and markov_stats['team_stats']:
                    st.markdown("---")
                    st.subheader("🏏 Team-wise Markov Chain Statistics")
                    st.info(f"Analyzing {len(markov_stats['teams_analyzed'])} unique teams: {', '.join(markov_stats['teams_analyzed'])}")
                
                st.markdown("---")
                st.subheader("Export for Simulation")
                
                # Convert stats to DataFrame for download
                stats_for_export = []
                for key, value in markov_stats.items():
                    if not isinstance(value, dict):
                        stats_for_export.append({'Statistic': key, 'Value': value})
                
                # Add phase-wise stats
                for phase in phases:
                    if f'{phase}_stats' in markov_stats and markov_stats[f'{phase}_stats']:
                        phase_data = markov_stats[f'{phase}_stats']
                        for stat_key, stat_value in phase_data.items():
                            stats_for_export.append({
                                'Statistic': f'{phase}_{stat_key}', 
                                'Value': stat_value
                            })
                
                export_df = pd.DataFrame(stats_for_export)
                st.download_button(
                    "Download Markov Chain Statistics CSV", 
                    to_csv(export_df), 
                    "markov_chain_statistics.csv", 
                    "text/csv"
                )
                
                st.info("""
                **How to use these statistics for Markov Chain simulation:**
                
                1. **State Definition**: Use phases (powerplay/middle/death) and current score as states
                2. **Transition Probabilities**: Use the runs distribution percentages for each phase
                3. **Wicket Modeling**: Use wicket percentages to model dismissals
                4. **Boundary Modeling**: Use four/six percentages for aggressive batting scenarios
                5. **Run Rate Targets**: Use phase-wise run rates for realistic scoring patterns
                """)
        
        elif json_page == "Venue-wise Statistics":
            st.subheader("Venue-wise Cricket Statistics")
            st.info("Analyze how different venues affect match outcomes, scoring patterns, and team strategies.")
            
            # Calculate venue-wise statistics
            venue_stats = calculate_venue_wise_stats(raw_data)
            
            if not venue_stats:
                st.warning("No venue data found in the uploaded files.")
            else:
                # Overview metrics
                total_venues = len(venue_stats)
                total_matches_analyzed = sum(stats['matches'] for stats in venue_stats.values())
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Venues", total_venues)
                with col2:
                    st.metric("Total Matches", total_matches_analyzed)
                with col3:
                    avg_matches_per_venue = total_matches_analyzed / total_venues if total_venues > 0 else 0
                    st.metric("Avg Matches per Venue", f"{avg_matches_per_venue:.1f}")
                
                st.markdown("---")
                
                # Venue comparison table
                st.subheader("Venue Comparison Overview")
                
                # Create DataFrame for venue comparison
                venue_comparison_data = []
                for venue, stats in venue_stats.items():
                    venue_comparison_data.append({
                        'Venue': venue,
                        'Matches': stats['matches'],
                        'Avg Run Rate': f"{stats['avg_run_rate']:.2f}",
                        'Avg 1st Innings': f"{stats['avg_first_innings']:.0f}",
                        'Avg 2nd Innings': f"{stats['avg_second_innings']:.0f}",
                        'Boundary %': f"{stats['boundary_percentage']:.1f}%",
                        'Dot Ball %': f"{stats['dot_ball_percentage']:.1f}%",
                        'Toss Win = Match Win': f"{stats['toss_win_match_win_rate']:.1f}%",
                        'Bat First Win Rate': f"{stats['bat_first_win_rate']:.1f}%"
                    })
                
                venue_df = pd.DataFrame(venue_comparison_data)
                st.dataframe(venue_df, use_container_width=True)
                
                # Download venue comparison
                st.download_button(
                    "Download Venue Comparison CSV",
                    to_csv(venue_df),
                    "venue_comparison.csv",
                    "text/csv"
                )
                
                st.markdown("---")
                
                # Detailed venue analysis
                st.subheader("Detailed Venue Analysis")
                
                # Venue selector
                selected_venue = st.selectbox(
                    "Select a venue for detailed analysis:",
                    options=list(venue_stats.keys()),
                    index=0
                )
                
                if selected_venue and selected_venue in venue_stats:
                    venue_data = venue_stats[selected_venue]
                    
                    st.write(f"### 🏟️ {selected_venue}")
                    
                    # Key metrics for selected venue
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Matches Played", venue_data['matches'])
                        st.metric("Avg Run Rate", f"{venue_data['avg_run_rate']:.2f}")
                    with col2:
                        st.metric("Highest Total", f"{venue_data['highest_team_total']:.0f}")
                        st.metric("Lowest Total", f"{venue_data['lowest_team_total']:.0f}")
                    with col3:
                        st.metric("Avg 1st Innings", f"{venue_data['avg_first_innings']:.0f}")
                        st.metric("Avg 2nd Innings", f"{venue_data['avg_second_innings']:.0f}")
                    with col4:
                        st.metric("Boundary %", f"{venue_data['boundary_percentage']:.1f}%")
                        st.metric("Wicket %", f"{venue_data['wicket_percentage']:.2f}%")
                    
                    st.markdown("---")
                    
                    # Phase-wise analysis for venue
                    st.write("**Phase-wise Scoring Patterns:**")
                    phase_col1, phase_col2, phase_col3 = st.columns(3)
                    
                    with phase_col1:
                        st.metric("Avg Powerplay Runs", f"{venue_data['avg_powerplay_runs']:.1f}")
                    with phase_col2:
                        st.metric("Avg Death Over Runs", f"{venue_data['avg_death_over_runs']:.1f}")
                    with phase_col3:
                        st.metric("Runs per Ball", f"{venue_data['avg_runs_per_ball']:.3f}")
                    
                    # Toss and decision impact
                    st.write("**Toss & Decision Impact:**")
                    toss_col1, toss_col2, toss_col3 = st.columns(3)
                    
                    with toss_col1:
                        st.metric("Toss Win = Match Win", f"{venue_data['toss_win_match_win_rate']:.1f}%")
                    with toss_col2:
                        st.metric("Bat First Win Rate", f"{venue_data['bat_first_win_rate']:.1f}%")
                    with toss_col3:
                        st.metric("Bowl First Win Rate", f"{venue_data['bowl_first_win_rate']:.1f}%")
                
                # Ball outcome probabilities for Markov chain modeling
                st.markdown("---")
                st.write("**Ball Outcome Probabilities (for Markov States):**")
                st.info("These probabilities are essential for Markov chain cricket simulation at this venue.")
                
                prob_cols = st.columns(4)
                for i in range(7):
                    col_idx = i % 4
                    prob_key = f'runs_{i}_probability'
                    if prob_key in venue_data:
                        prob_cols[col_idx].metric(f"{i} Runs", f"{venue_data[prob_key]:.2f}%")
                
                # Create visualization for venue-specific runs distribution
                venue_runs_data = []
                for i in range(7):
                    prob_key = f'runs_{i}_probability'
                    if prob_key in venue_data:
                        venue_runs_data.append({
                            'Runs': str(i),
                            'Probability': venue_data[prob_key]
                        })
                
                if venue_runs_data:
                    venue_runs_df = pd.DataFrame(venue_runs_data)
                    fig_venue_runs = px.bar(
                        venue_runs_df, 
                        x='Runs', 
                        y='Probability',
                        title=f'Ball Outcome Probabilities at {selected_venue}',
                        labels={'Probability': 'Probability (%)'}
                    )
                    st.plotly_chart(fig_venue_runs, use_container_width=True)
                
                st.markdown("---")
                
                # Venue comparisons with visualizations
                st.subheader("Venue Comparisons")
                
                # Create visualizations
                if len(venue_stats) > 1:
                    # Run rate comparison
                    run_rate_data = []
                    for venue, stats in venue_stats.items():
                        run_rate_data.append({
                            'Venue': venue[:20] + '...' if len(venue) > 20 else venue,  # Truncate long names
                            'Run Rate': stats['avg_run_rate'],
                            'Matches': stats['matches']
                        })
                    
                    run_rate_df = pd.DataFrame(run_rate_data)
                    fig_run_rate = px.bar(
                        run_rate_df, 
                        x='Venue', 
                        y='Run Rate',
                        title='Average Run Rate by Venue',
                        hover_data=['Matches']
                    )
                    fig_run_rate.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_run_rate, use_container_width=True)
                    
                    # Boundary percentage comparison
                    boundary_data = []
                    for venue, stats in venue_stats.items():
                        boundary_data.append({
                            'Venue': venue[:20] + '...' if len(venue) > 20 else venue,
                            'Boundary %': stats['boundary_percentage'],
                            'Four %': stats['four_percentage'],
                            'Six %': stats['six_percentage']
                        })
                    
                    boundary_df = pd.DataFrame(boundary_data)
                    fig_boundary = px.bar(
                        boundary_df, 
                        x='Venue', 
                        y='Boundary %',
                        title='Boundary Percentage by Venue',
                        hover_data=['Four %', 'Six %']
                    )
                    fig_boundary.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_boundary, use_container_width=True)
                    
                    # First vs Second innings comparison
                    innings_data = []
                    for venue, stats in venue_stats.items():
                        venue_short = venue[:15] + '...' if len(venue) > 15 else venue
                        innings_data.extend([
                            {'Venue': venue_short, 'Innings': '1st Innings', 'Average Score': stats['avg_first_innings']},
                            {'Venue': venue_short, 'Innings': '2nd Innings', 'Average Score': stats['avg_second_innings']}
                        ])
                    
                    innings_df = pd.DataFrame(innings_data)
                    fig_innings = px.bar(
                        innings_df, 
                        x='Venue', 
                        y='Average Score',
                        color='Innings',
                        title='First vs Second Innings Average Scores by Venue',
                        barmode='group'
                    )
                    fig_innings.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_innings, use_container_width=True)
                
                # Export detailed venue statistics
                st.markdown("---")
                st.subheader("Export Venue Statistics")
                
                # Create detailed export data
                detailed_venue_data = []
                for venue, stats in venue_stats.items():
                    detailed_venue_data.append({
                        'Venue': venue,
                        'Matches': stats['matches'],
                        'Avg_Run_Rate': stats['avg_run_rate'],
                        'Avg_Runs_Per_Ball': stats['avg_runs_per_ball'],
                        'Dot_Ball_Percentage': stats['dot_ball_percentage'],
                        'Four_Percentage': stats['four_percentage'],
                        'Six_Percentage': stats['six_percentage'],
                        'Boundary_Percentage': stats['boundary_percentage'],
                        'Wicket_Percentage': stats['wicket_percentage'],
                        'Avg_First_Innings': stats['avg_first_innings'],
                        'Avg_Second_Innings': stats['avg_second_innings'],
                        'Avg_Powerplay_Runs': stats['avg_powerplay_runs'],
                        'Avg_Death_Over_Runs': stats['avg_death_over_runs'],
                        'Highest_Team_Total': stats['highest_team_total'],
                        'Lowest_Team_Total': stats['lowest_team_total'],
                        'Toss_Win_Match_Win_Rate': stats['toss_win_match_win_rate'],
                        'Bat_First_Win_Rate': stats['bat_first_win_rate'],
                        'Bowl_First_Win_Rate': stats['bowl_first_win_rate']
                    })
                
                detailed_venue_df = pd.DataFrame(detailed_venue_data)
                st.download_button(
                    "Download Detailed Venue Statistics CSV",
                    to_csv(detailed_venue_df),
                    "detailed_venue_statistics.csv",
                    "text/csv"
                )
                
                st.info("""
                **How to use venue statistics for analysis:**
                
                1. **Home Advantage**: Compare team performance at different venues
                2. **Pitch Conditions**: Use run rates and boundary percentages to understand pitch behavior
                3. **Toss Impact**: Analyze whether to bat or bowl first at specific venues
                4. **Match Simulation**: Use venue-specific statistics for more accurate predictions
                5. **Team Strategy**: Adapt game plans based on venue characteristics
                """)
        
        elif json_page == "Team-wise Statistics":
            st.subheader("Team-wise Cricket Statistics")
            st.info("Comprehensive analysis of team performance, batting/bowling patterns, and head-to-head comparisons.")
            
            # Calculate team-wise statistics
            team_stats = calculate_team_wise_stats(raw_data)
            
            if not team_stats:
                st.warning("No team data found in the uploaded files.")
            else:
                # Overview metrics
                total_teams = len(team_stats)
                total_matches_analyzed = sum(stats['matches_played'] for stats in team_stats.values()) // 2  # Divide by 2 since each match involves 2 teams
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total Teams", total_teams)
                with col2:
                    st.metric("Total Matches", total_matches_analyzed)
                with col3:
                    avg_matches_per_team = sum(stats['matches_played'] for stats in team_stats.values()) / total_teams if total_teams > 0 else 0
                    st.metric("Avg Matches per Team", f"{avg_matches_per_team:.1f}")
                
                st.markdown("---")
                
                # Team comparison table
                st.subheader("Team Performance Overview")
                
                # Create DataFrame for team comparison
                team_comparison_data = []
                for team, stats in team_stats.items():
                    team_comparison_data.append({
                        'Team': team,
                        'Matches': stats['matches_played'],
                        'Win %': f"{stats['win_percentage']:.1f}%",
                        'Avg Score': f"{stats['avg_score']:.0f}",
                        'Strike Rate': f"{stats['strike_rate']:.1f}",
                        'Boundary %': f"{stats['boundary_percentage']:.1f}%",
                        'Bowling Economy': f"{stats['bowling_economy']:.2f}",
                        'Toss Win %': f"{stats['toss_win_percentage']:.1f}%",
                        'Venues': stats['venues_played']
                    })
                
                team_df = pd.DataFrame(team_comparison_data)
                # Sort by win percentage
                team_df = team_df.sort_values('Win %', ascending=False, key=lambda x: x.str.rstrip('%').astype(float))
                st.dataframe(team_df, use_container_width=True)
                
                # Download team comparison
                st.download_button(
                    "Download Team Comparison CSV",
                    to_csv(team_df),
                    "team_comparison.csv",
                    "text/csv"
                )
                
                st.markdown("---")
                
                # Detailed team analysis
                st.subheader("Detailed Team Analysis")
                
                # Team selector
                selected_team = st.selectbox(
                    "Select a team for detailed analysis:",
                    options=list(team_stats.keys()),
                    index=0
                )
                
                if selected_team and selected_team in team_stats:
                    team_data = team_stats[selected_team]
                    
                    st.write(f"### 🏏 {selected_team}")
                    
                    # Match record
                    st.write("**Match Record:**")
                    record_col1, record_col2, record_col3, record_col4 = st.columns(4)
                    with record_col1:
                        st.metric("Matches Played", team_data['matches_played'])
                    with record_col2:
                        st.metric("Wins", team_data['matches_won'])
                        st.metric("Win %", f"{team_data['win_percentage']:.1f}%")
                    with record_col3:
                        st.metric("Losses", team_data['matches_lost'])
                        st.metric("Loss %", f"{team_data['loss_percentage']:.1f}%")
                    with record_col4:
                        st.metric("No Results", team_data['no_results'])
                        st.metric("Venues Played", team_data['venues_played'])
                    
                    st.markdown("---")
                    
                    # Batting statistics
                    st.write("**Batting Performance:**")
                    bat_col1, bat_col2, bat_col3, bat_col4 = st.columns(4)
                    with bat_col1:
                        st.metric("Avg Score", f"{team_data['avg_score']:.0f}")
                        st.metric("Highest Score", team_data['highest_score'])
                    with bat_col2:
                        st.metric("Strike Rate", f"{team_data['strike_rate']:.1f}")
                        st.metric("Run Rate", f"{team_data['avg_run_rate']:.2f}")
                    with bat_col3:
                        st.metric("Boundary %", f"{team_data['boundary_percentage']:.1f}%")
                        st.metric("Dot Ball %", f"{team_data['dot_ball_percentage']:.1f}%")
                    with bat_col4:
                        st.metric("Fours Hit", team_data['total_fours_hit'])
                        st.metric("Sixes Hit", team_data['total_sixes_hit'])
                    
                    # Phase-wise batting
                    st.write("**Phase-wise Batting:**")
                    phase_bat_col1, phase_bat_col2 = st.columns(2)
                    with phase_bat_col1:
                        st.metric("Avg Powerplay Runs", f"{team_data['avg_powerplay_runs']:.1f}")
                    with phase_bat_col2:
                        st.metric("Avg Death Over Runs", f"{team_data['avg_death_over_runs']:.1f}")
                    
                    st.markdown("---")
                    
                    # Bowling statistics
                    st.write("**Bowling Performance:**")
                    bowl_col1, bowl_col2, bowl_col3, bowl_col4 = st.columns(4)
                    with bowl_col1:
                        st.metric("Economy Rate", f"{team_data['bowling_economy']:.2f}")
                        st.metric("Strike Rate", f"{team_data['bowling_strike_rate']:.1f}")
                    with bowl_col2:
                        st.metric("Wickets Taken", team_data['total_wickets_taken'])
                        st.metric("Dots Bowled", team_data['total_dots_bowled'])
                    with bowl_col3:
                        st.metric("Avg PP Runs Conceded", f"{team_data['avg_powerplay_runs_conceded']:.1f}")
                    with bowl_col4:
                        st.metric("Avg Death Runs Conceded", f"{team_data['avg_death_over_runs_conceded']:.1f}")
                    
                    st.markdown("---")
                    
                    # Toss and decision impact
                    st.write("**Toss & Decision Analysis:**")
                    toss_col1, toss_col2, toss_col3, toss_col4 = st.columns(4)
                    with toss_col1:
                        st.metric("Toss Win %", f"{team_data['toss_win_percentage']:.1f}%")
                    with toss_col2:
                        st.metric("Toss Win → Match Win", f"{team_data['toss_win_match_win_rate']:.1f}%")
                    with toss_col3:
                        st.metric("Bat First Win Rate", f"{team_data['bat_first_win_rate']:.1f}%")
                    with toss_col4:
                        st.metric("Bowl First Win Rate", f"{team_data['bowl_first_win_rate']:.1f}%")
                
                # Ball outcome probabilities for Markov chain modeling
                st.markdown("---")
                st.write("**Ball Outcome Probabilities (for Markov States):**")
                st.info("These probabilities show how this team typically scores runs per ball - essential for Markov chain simulation.")
                
                prob_cols = st.columns(4)
                for i in range(7):
                    col_idx = i % 4
                    prob_key = f'runs_{i}_probability'
                    if prob_key in team_data:
                        prob_cols[col_idx].metric(f"{i} Runs", f"{team_data[prob_key]:.2f}%")
                
                # Create visualization for team-specific runs distribution
                team_runs_data = []
                for i in range(7):
                    prob_key = f'runs_{i}_probability'
                    if prob_key in team_data:
                        team_runs_data.append({
                            'Runs': str(i),
                            'Probability': team_data[prob_key]
                        })
                
                if team_runs_data:
                    team_runs_df = pd.DataFrame(team_runs_data)
                    fig_team_runs = px.bar(
                        team_runs_df, 
                        x='Runs', 
                        y='Probability',
                        title=f'Ball Outcome Probabilities for {selected_team}',
                        labels={'Probability': 'Probability (%)'}
                    )
                    st.plotly_chart(fig_team_runs, use_container_width=True)
                
                st.markdown("---")
                
                # Team comparisons with visualizations
                st.subheader("Team Performance Comparisons")
                
                if len(team_stats) > 1:
                    # Win percentage comparison
                    win_data = []
                    for team, stats in team_stats.items():
                        win_data.append({
                            'Team': team,
                            'Win %': stats['win_percentage'],
                            'Matches': stats['matches_played']
                        })
                    
                    win_df = pd.DataFrame(win_data)
                    win_df = win_df.sort_values('Win %', ascending=True)  # Sort for better visualization
                    fig_win = px.bar(
                        win_df, 
                        x='Win %', 
                        y='Team',
                        orientation='h',
                        title='Win Percentage by Team',
                        hover_data=['Matches']
                    )
                    st.plotly_chart(fig_win, use_container_width=True)
                    
                    # Batting vs Bowling performance
                    performance_data = []
                    for team, stats in team_stats.items():
                        performance_data.append({
                            'Team': team,
                            'Strike Rate': stats['strike_rate'],
                            'Economy Rate': stats['bowling_economy'],
                            'Avg Score': stats['avg_score']
                        })
                    
                    perf_df = pd.DataFrame(performance_data)
                    fig_perf = px.scatter(
                        perf_df, 
                        x='Strike Rate', 
                        y='Economy Rate',
                        size='Avg Score',
                        hover_name='Team',
                        title='Batting Strike Rate vs Bowling Economy Rate',
                        labels={'Strike Rate': 'Batting Strike Rate', 'Economy Rate': 'Bowling Economy Rate'}
                    )
                    st.plotly_chart(fig_perf, use_container_width=True)
                    
                    # Phase-wise performance comparison
                    phase_data = []
                    for team, stats in team_stats.items():
                        phase_data.extend([
                            {'Team': team, 'Phase': 'Powerplay', 'Runs Scored': stats['avg_powerplay_runs'], 'Runs Conceded': stats['avg_powerplay_runs_conceded']},
                            {'Team': team, 'Phase': 'Death Overs', 'Runs Scored': stats['avg_death_over_runs'], 'Runs Conceded': stats['avg_death_over_runs_conceded']}
                        ])
                    
                    phase_df = pd.DataFrame(phase_data)
                    
                    # Runs scored comparison
                    fig_phase_scored = px.bar(
                        phase_df, 
                        x='Team', 
                        y='Runs Scored',
                        color='Phase',
                        title='Phase-wise Runs Scored by Team',
                        barmode='group'
                    )
                    fig_phase_scored.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_phase_scored, use_container_width=True)
                    
                    # Runs conceded comparison
                    fig_phase_conceded = px.bar(
                        phase_df, 
                        x='Team', 
                        y='Runs Conceded',
                        color='Phase',
                        title='Phase-wise Runs Conceded by Team',
                        barmode='group'
                    )
                    fig_phase_conceded.update_xaxes(tickangle=45)
                    st.plotly_chart(fig_phase_conceded, use_container_width=True)
                
                # Export detailed team statistics
                st.markdown("---")
                st.subheader("Export Team Statistics")
                
                # Create detailed export data
                detailed_team_data = []
                for team, stats in team_stats.items():
                    detailed_team_data.append({
                        'Team': team,
                        'Matches_Played': stats['matches_played'],
                        'Matches_Won': stats['matches_won'],
                        'Win_Percentage': stats['win_percentage'],
                        'Avg_Score': stats['avg_score'],
                        'Highest_Score': stats['highest_score'],
                        'Lowest_Score': stats['lowest_score'],
                        'Strike_Rate': stats['strike_rate'],
                        'Avg_Run_Rate': stats['avg_run_rate'],
                        'Boundary_Percentage': stats['boundary_percentage'],
                        'Dot_Ball_Percentage': stats['dot_ball_percentage'],
                        'Avg_Powerplay_Runs': stats['avg_powerplay_runs'],
                        'Avg_Death_Over_Runs': stats['avg_death_over_runs'],
                        'Bowling_Economy': stats['bowling_economy'],
                        'Bowling_Strike_Rate': stats['bowling_strike_rate'],
                        'Total_Wickets_Taken': stats['total_wickets_taken'],
                        'Toss_Win_Percentage': stats['toss_win_percentage'],
                        'Toss_Win_Match_Win_Rate': stats['toss_win_match_win_rate'],
                        'Bat_First_Win_Rate': stats['bat_first_win_rate'],
                        'Bowl_First_Win_Rate': stats['bowl_first_win_rate'],
                        'Venues_Played': stats['venues_played'],
                        'Opponents_Faced': stats['opponents_faced']
                    })
                
                detailed_team_df = pd.DataFrame(detailed_team_data)
                st.download_button(
                    "Download Detailed Team Statistics CSV",
                    to_csv(detailed_team_df),
                    "detailed_team_statistics.csv",
                    "text/csv"
                )
                
                st.info("""
                **How to use team statistics for analysis:**
                
                1. **Performance Evaluation**: Compare teams across batting, bowling, and overall performance
                2. **Strategy Planning**: Use phase-wise statistics to plan game strategies
                3. **Head-to-Head Analysis**: Compare specific teams for match predictions
                4. **Toss Decision**: Analyze whether teams perform better batting or bowling first
                5. **Venue Adaptation**: Understand how teams perform across different venues
                6. **Player Selection**: Use team patterns to inform player selection strategies
                """)
    else:
        st.info("Please upload one or more JSON files to begin analysis.")

elif page == "CSV Market Analyzer":
    st.header("CSV Betting Market Analyzer")
    st.info("Upload a CSV file (like the 'all_market_summaries.csv' generated by this app) to analyze trends.")
    
    csv_file = st.file_uploader("Upload Market Summary CSV", type=["csv"])
    
    if csv_file:
        df = pd.read_csv(csv_file)
        st.subheader("Uploaded Data Preview")
        st.dataframe(df.head())
        
        st.sidebar.subheader("CSV Analyzer Views")
        analysis_type = st.sidebar.radio("Choose Analysis Type", ["Descriptive Statistics", "Frequency Analysis", "Toss Analysis"])
        st.markdown("---")
        
        if analysis_type == "Descriptive Statistics":
            st.subheader("Descriptive Statistics")
            st.write("Summary of numerical columns in your data.")
            st.dataframe(df.describe())
            
        elif analysis_type == "Frequency Analysis":
            display_frequency_analysis(df)
            
        elif analysis_type == "Toss Analysis":
            display_toss_analysis(df)
