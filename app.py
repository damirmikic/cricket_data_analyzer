import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(layout="wide")

# --- Helper Functions ---

def calculate_markov_chain_stats(data_list):
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
        json_page = st.sidebar.radio("Choose a data view", ["Match Summaries", "Aggregated Batting Stats", "Aggregated Bowling Stats", "Combined Ball-by-Ball", "Betting Market Summaries", "Markov Chain Statistics"])
        
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
            
            # Calculate Markov chain statistics
            markov_stats = calculate_markov_chain_stats(raw_data)
            
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
                
                # Export statistics for use in simulation
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