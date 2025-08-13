import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(layout="wide")

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
    
    # Extract all deliveries from all matches
    for data in data_list:
        for inning in data.get('innings', []):
            inning_team = inning.get('team', 'Unknown')
            for over in inning.get('overs', []):
                over_num = over.get('over', 0)
                for ball_num, delivery in enumerate(over.get('deliveries', [])):
                    # Skip extras (wides, no-balls) for ball-by-ball analysis
                    if 'extras' not in delivery or not any(k in delivery['extras'] for k in ['wides', 'noballs']):
                        delivery_info = {
                            'team': inning_team,
                            'over': over_num,
                            'ball': ball_num + 1,
                            'runs_off_bat': delivery['runs']['batter'],
                            'total_runs': delivery['runs']['total'],
                            'extras': delivery['runs']['extras'],
                            'is_wicket': 'wickets' in delivery,
                            'is_four': delivery['runs']['batter'] == 4,
                            'is_six': delivery['runs']['batter'] == 6,
                            'is_dot': delivery['runs']['total'] == 0,
                            'is_single': delivery['runs']['batter'] == 1,
                            'phase': 'powerplay' if over_num < 6 else 'middle' if over_num < 15 else 'death'
                        }
                        all_deliveries.append(delivery_info)
    
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
        'death_overs_stats': {}
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
        stats = {'team': inning_data.get('team', f'Innings {i+1}'),'total_runs': 0,'powerplay_runs': 0,'runs_overs_7_13': 0, 'runs_overs_14_20': 0, 'highest_over': 0,'fall_of_1st_wicket': 'N/A', 'runs_per_over': []}
        running_score = 0
        wicket_fell = False
        for over in inning_data.get('overs', []):
            over_num = over.get('over', -1)
            over_runs = sum(d['runs']['total'] for d in over.get('deliveries', []))
            
            stats['runs_per_over'].append(over_runs)
            if over_runs > stats['highest_over']: stats['highest_over'] = over_runs
            
            if over_num < 6: stats['powerplay_runs'] += over_runs
            if 6 <= over_num <= 12: stats['runs_overs_7_13'] += over_runs
            if 13 <= over_num <= 19: stats['runs_overs_14_20'] += over_runs

            has_four = any(d['runs']['batter'] == 4 for d in over.get('deliveries', []))
            has_six = any(d['runs']['batter'] == 6 for d in over.get('deliveries', []))
            if has_four and has_six: four_and_six_in_over = "Yes"
            if any('wickets' in d for d in over.get('deliveries', [])): overs_with_wicket += 1
                
            if not wicket_fell:
                for delivery in over.get('deliveries', []):
                    running_score += delivery['runs']['total']
                    if 'wickets' in delivery:
                        stats['fall_of_1st_wicket'] = running_score
                        wicket_fell = True
                        break
        stats['total_runs'] = sum(d['runs']['total'] for o in inning_data.get('overs', []) for d in o.get('deliveries', []))
        inning_stats.append(stats)
        
    summary_dict = {
        'match_id': data.get('match_id', 'N/A'),
        'Match Winner': winner,
        'Tied Match': 'Yes' if info.get('outcome', {}).get('result') == 'tie' else 'No',
        'Innings 1 Team': inning_stats[0]['team'] if len(inning_stats) > 0 else 'N/A',
        'Innings 1 Runs': inning_stats[0]['total_runs'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs (Overs 1-6)': inning_stats[0]['powerplay_runs'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs (Overs 7-13)': inning_stats[0]['runs_overs_7_13'] if len(inning_stats) > 0 else 0,
        'Innings 1 Runs (Overs 14-20)': inning_stats[0]['runs_overs_14_20'] if len(inning_stats) > 0 else 0,
        'Innings 2 Team': inning_stats[1]['team'] if len(inning_stats) > 1 else 'N/A',
        'Innings 2 Runs': inning_stats[1]['total_runs'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs (Overs 1-6)': inning_stats[1]['powerplay_runs'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs (Overs 7-13)': inning_stats[1]['runs_overs_7_13'] if len(inning_stats) > 1 else 0,
        'Innings 2 Runs (Overs 14-20)': inning_stats[1]['runs_overs_14_20'] if len(inning_stats) > 1 else 0,
        'Top Batsman Match': batting_df.iloc[0]['player_name'] if not batting_df.empty else 'N/A',
        'Top Batsman Runs': batting_df.iloc[0]['runs'] if not batting_df.empty else 'N/A',
        'Man of the Match': info.get('player_of_match', ['N/A'])[0],
        'Toss Winner': info.get('toss', {}).get('winner', 'N/A'),
        'Four and Six in an Over': four_and_six_in_over,
        'Overs with a Wicket': overs_with_wicket
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

st.sidebar.header("Upload Data")
json_files = st.sidebar.file_uploader("Upload JSON match files", type=["json"], accept_multiple_files=True)

st.sidebar.header("Navigation")
# Always show JSON analyzer. Show CSV analyzer only if JSONs are uploaded.
nav_options = ["JSON Data Analyzer"]
if json_files:
    nav_options.append("CSV Market Analyzer")
page = st.sidebar.radio("Choose an analyzer", nav_options)


if page == "JSON Data Analyzer":
    if json_files:
        raw_data, match_summary, bbb, batting_summary, bowling_summary, market_summaries_df = process_all_files(json_files)

        st.sidebar.subheader("JSON Analyzer Views")
        json_page = st.sidebar.radio("Choose a data view", ["Match Summaries", "Aggregated Batting Stats", "Aggregated Bowling Stats", "Combined Ball-by-Ball", "Betting Market Summaries", "Markov Chain Statistics", "Venue-wise Statistics", "Team-wise Statistics"])
        
        st.header(f"Analysis of {len(json_files)} Match(es)")
        st.markdown("---")

        if json_page == "Match Summaries":
            st.subheader("Match Summaries (Standardized)")
            st.dataframe(match_summary)
            st.download_button("Download Summaries CSV", to_csv(match_summary), "match_summaries.csv", "text/csv")
        
        elif json_page == "Aggregated Batting Stats":
            st.subheader("Aggregated Player Batting Stats")
            st.dataframe(batting_summary)
            st.download_button("Download Batting CSV", to_csv(batting_summary), "aggregated_batting_summary.csv", "text/csv")
        
        elif json_page == "Aggregated Bowling Stats":
            st.subheader("Aggregated Player Bowling Stats")
            st.dataframe(bowling_summary)
            st.download_button("Download Bowling CSV", to_csv(bowling_summary), "aggregated_bowling_summary.csv", "text/csv")
        
        elif json_page == "Combined Ball-by-Ball":
            st.subheader("Combined Ball-by-Ball Data")
            st.dataframe(bbb)
            st.download_button("Download Ball-by-Ball CSV", to_csv(bbb), "combined_ball_by_ball.csv", "text/csv")
        
        elif json_page == "Betting Market Summaries":
            st.subheader("Betting Market Summaries")
            if not market_summaries_df.empty:
                st.download_button(label="Download All Summaries (Concatenated CSV)",data=to_csv(market_summaries_df),file_name="all_market_summaries.csv",mime="text/csv")
                st.markdown("---")
                st.info("Displaying individual summaries for each match uploaded.")
                for match_summary_dict in market_summaries_df.to_dict('records'):
                    match_id = match_summary_dict.get('match_id', 'Unknown_Match')
                    with st.expander(f"**Match ID: {match_id}**"):
                        col1, col2 = st.columns(2)
                        for i, (key, value) in enumerate(match_summary_dict.items()):
                            if i % 2 == 0: col1.markdown(f"**{key}:** {value}")
                            else: col2.markdown(f"**{key}:** {value}")
                        single_match_df = pd.DataFrame([match_summary_dict])
                        st.download_button(label=f"Download Summary for {match_id}",data=to_csv(single_match_df),file_name=f"market_summary_{match_id.replace('.json','')}.csv",mime="text/csv",key=f"download_{match_id}")
            else:
                st.warning("Could not generate market summaries from the uploaded files.")
        
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
                    fig_run_rate.update_xaxis(tickangle=45)
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
                    fig_boundary.update_xaxis(tickangle=45)
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
                    fig_innings.update_xaxis(tickangle=45)
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
                    fig_phase_scored.update_xaxis(tickangle=45)
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
                    fig_phase_conceded.update_xaxis(tickangle=45)
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