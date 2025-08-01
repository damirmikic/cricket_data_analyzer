import streamlit as st
import pandas as pd
import json
import plotly.express as px

st.set_page_config(
    page_title="Cricket Data Analyzer | Match & Betting Market Summaries",
    page_icon="🏏",
    layout="wide",
    menu_items={
        'About': "This app analyzes cricket match data from JSON files to provide detailed insights and betting market summaries."
    }
)

# --- Helper Functions ---

def to_csv(df):
    """Converts a DataFrame to a CSV string for downloading."""
    return df.to_csv(index=False).encode('utf-8')

def get_run_details(delivery):
    """
    Safely extracts run details from a delivery object, handling both dict and int formats for the 'runs' field.
    """
    runs_obj = delivery.get('runs', 0)
    if isinstance(runs_obj, dict):
        return {
            'batter': runs_obj.get('batter', 0),
            'extras': runs_obj.get('extras', 0),
            'total': runs_obj.get('total', 0),
            'wides': runs_obj.get('extras', {}).get('wides', 0) if isinstance(runs_obj.get('extras'), dict) else 0
        }
    elif isinstance(runs_obj, int):
        return {'batter': runs_obj, 'extras': 0, 'total': runs_obj, 'wides': 0}
    return {'batter': 0, 'extras': 0, 'total': 0, 'wides': 0}


@st.cache_data
def get_player_summaries_single_match(data):
    """Creates DataFrames for player batting and bowling summaries for a single match."""
    info = data.get('info', {})
    player_stats = {p: {'team': t, 'runs': 0, 'balls_faced': 0, 'fours': 0, 'sixes': 0, 'runs_conceded': 0, 'balls_bowled': 0, 'wickets': 0} for t, ps in info.get('players', {}).items() for p in ps}

    for inning in data.get('innings', []):
        for over in inning.get('overs', []):
            for delivery in over.get('deliveries', []):
                batter, bowler = delivery.get('batter'), delivery.get('bowler')
                runs = get_run_details(delivery)
                
                if batter in player_stats:
                    player_stats[batter]['runs'] += runs['batter']
                    player_stats[batter]['balls_faced'] += 1
                    if runs['batter'] == 4: player_stats[batter]['fours'] += 1
                    if runs['batter'] == 6: player_stats[batter]['sixes'] += 1
                
                if bowler in player_stats:
                    player_stats[bowler]['runs_conceded'] += runs['total']
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

    return batting_df, bowling_df

def get_inning_stats(innings):
    """Helper to calculate detailed stats for each inning."""
    inning_stats = []
    for i, inning_data in enumerate(innings):
        stats = {'team': inning_data.get('team', f'Innings {i+1}'),'total_runs': 0,'powerplay_runs': 0,'runs_overs_7_13': 0, 'runs_overs_14_20': 0, 'highest_over': 0,'fall_of_1st_wicket': 'N/A', 'fours': 0, 'sixes': 0, 'wickets': 0}
        running_score = 0
        wicket_fell = False
        for over in inning_data.get('overs', []):
            over_num = over.get('over', -1)
            deliveries = over.get('deliveries', [])
            over_runs = sum(get_run_details(d)['total'] for d in deliveries)
            if over_runs > stats['highest_over']: stats['highest_over'] = over_runs
            if over_num < 6: stats['powerplay_runs'] += over_runs
            if 6 <= over_num <= 12: stats['runs_overs_7_13'] += over_runs
            if 13 <= over_num <= 19: stats['runs_overs_14_20'] += over_runs
            for delivery in deliveries:
                runs = get_run_details(delivery)
                if runs['batter'] == 4: stats['fours'] += 1
                if runs['batter'] == 6: stats['sixes'] += 1
                if 'wickets' in delivery: stats['wickets'] += 1
                if not wicket_fell:
                    running_score += runs['total']
                    if 'wickets' in delivery:
                        stats['fall_of_1st_wicket'] = running_score
                        wicket_fell = True
        stats['total_runs'] = sum(get_run_details(d)['total'] for o in inning_data.get('overs', []) for d in o.get('deliveries', []))
        inning_stats.append(stats)
    return inning_stats

def get_betting_market_summary_dict(data):
    """Generates a dictionary of betting market outcomes for a single match with standardized keys."""
    info = data.get('info', {})
    innings = data.get('innings', [])
    batting_df, _ = get_player_summaries_single_match(data)
    inning_stats = get_inning_stats(innings)
    
    winner = info.get('outcome', {}).get('winner', 'No Result')

    inn1_fow = inning_stats[0]['fall_of_1st_wicket'] if len(inning_stats) > 0 and isinstance(inning_stats[0]['fall_of_1st_wicket'], int) else 0
    inn2_fow = inning_stats[1]['fall_of_1st_wicket'] if len(inning_stats) > 1 and isinstance(inning_stats[1]['fall_of_1st_wicket'], int) else 0
    highest_opening_partnership = inning_stats[0]['team'] if len(inning_stats) > 0 and inn1_fow >= inn2_fow else (inning_stats[1]['team'] if len(inning_stats) > 1 else 'N/A')
    
    top_batsman_name, top_batsman_runs = "N/A", 0
    if not batting_df.empty:
        top_performer = batting_df.sort_values('runs', ascending=False).iloc[0]
        top_batsman_name, top_batsman_runs = top_performer['player_name'], top_performer['runs']

    players_50 = ", ".join(batting_df[batting_df['runs'] >= 50]['player_name'].tolist()) if not batting_df.empty else "None"
    players_100 = ", ".join(batting_df[batting_df['runs'] >= 100]['player_name'].tolist()) if not batting_df.empty else "None"

    return {
        'match_id': data.get('match_id', 'N/A'),
        'season': info.get('season', 'N/A'),
        'Match Winner': winner,
        'Highest Opening Partnership': highest_opening_partnership,
        'Top Batsman Match': top_batsman_name,
        'Top Batsman Runs': top_batsman_runs,
        'Batsmen to Score 50+': players_50 if players_50 else "None",
        'Batsmen to Score 100+': players_100 if players_100 else "None",
        'Man of the Match': info.get('player_of_match', ['N/A'])[0],
        'Toss Winner': info.get('toss', {}).get('winner', 'N/A'),
        # ... other markets ...
    }

def get_statistical_summary(data):
    """Generates a dictionary of binary-encoded and total-based market outcomes."""
    info = data.get('info', {})
    home_team, away_team = info.get('teams', ['N/A', 'N/A'])[:2]
    winner = info.get('outcome', {}).get('winner')
    toss_winner = info.get('toss', {}).get('winner')
    inning_stats = get_inning_stats(data.get('innings', []))
    
    home_inning_stats = next((s for s in inning_stats if s['team'] == home_team), None)
    away_inning_stats = next((s for s in inning_stats if s['team'] == away_team), None)

    def encode_winner(val1, val2):
        if val1 > val2: return 1
        if val2 > val1: return 2
        return 0

    summary = {
        'match_id': data.get('match_id', 'N/A'),
        'Match_Winner': 1 if winner == home_team else (2 if winner == away_team else 0),
        'Toss_Winner': 1 if toss_winner == home_team else 2,
    }
    if home_inning_stats and away_inning_stats:
        summary.update({
            'Home_Runs': home_inning_stats['total_runs'],
            'Away_Runs': away_inning_stats['total_runs'],
            'Most_Powerplay_Runs': encode_winner(home_inning_stats['powerplay_runs'], away_inning_stats['powerplay_runs']),
            'Most_Fours': encode_winner(home_inning_stats['fours'], away_inning_stats['fours']),
            'Most_Sixes': encode_winner(home_inning_stats['sixes'], away_inning_stats['sixes']),
            'Highest_Opening_Partnership': encode_winner(
                home_inning_stats.get('fall_of_1st_wicket', 0) if isinstance(home_inning_stats.get('fall_of_1st_wicket'), int) else 0,
                away_inning_stats.get('fall_of_1st_wicket', 0) if isinstance(away_inning_stats.get('fall_of_1st_wicket'), int) else 0
            ),
        })
    return summary


def get_runs_per_over_summary(data):
    """Calculates the cumulative runs at the end of each over for each inning."""
    all_over_summaries = []
    for i, inning_data in enumerate(data.get('innings', [])):
        running_total = 0
        for over_data in inning_data.get('overs', []):
            over_number = over_data.get('over', -1) + 1
            over_runs = sum(get_run_details(d)['total'] for d in over_data.get('deliveries', []))
            running_total += over_runs
            all_over_summaries.append({'match_id': data.get('match_id', 'N/A'),'inning': i + 1,'team': inning_data.get('team', 'N/A'),'over': over_number,'runs_in_over': over_runs,'cumulative_runs': running_total})
    return pd.DataFrame(all_over_summaries)

# --- Main Data Processing Function ---

@st.cache_data
def process_all_files(uploaded_files):
    """Processes a list of uploaded JSON files and aggregates all data."""
    all_match_data, all_market_summaries, all_match_summaries, all_ball_by_ball, all_batting, all_bowling, all_runs_per_over, all_stat_summaries = [], [], [], [], [], [], [], []

    for uploaded_file in uploaded_files:
        try:
            data = json.loads(uploaded_file.getvalue())
            match_id = uploaded_file.name
            data['match_id'] = match_id
            
            all_match_data.append(data)
            all_market_summaries.append(get_betting_market_summary_dict(data))
            all_runs_per_over.append(get_runs_per_over_summary(data))
            all_stat_summaries.append(get_statistical_summary(data))
            
            info, innings = data.get('info', {}), data.get('innings', [])
            home_team, away_team = info.get('teams', ['N/A', 'N/A'])[:2]
            winner = info.get('outcome', {}).get('winner', 'No Result')

            home_score = sum(get_run_details(d)['total'] for o in innings[0]['overs'] for d in o['deliveries']) if len(innings) > 0 else 0
            away_score = sum(get_run_details(d)['total'] for o in innings[1]['overs'] for d in o['deliveries']) if len(innings) > 1 else 0
            all_match_summaries.append({'match_id': match_id, 'date': info.get('dates', ['N/A'])[0], 'home_team': home_team, 'away_team': away_team,'toss_winner': info.get('toss', {}).get('winner', 'N/A'), 'toss_decision': info.get('toss', {}).get('decision', 'N/A'),'winner': winner, 'home_score': home_score, 'away_score': away_score, 'venue': info.get('venue', 'N/A')})
            
            for i, inning in enumerate(innings):
                for over in inning.get('overs', []):
                    for j, delivery in enumerate(over.get('deliveries', [])):
                        runs = get_run_details(delivery)
                        all_ball_by_ball.append({'match_id': match_id, 'inning': i + 1, 'over': over['over'] + 1, 'ball': j + 1, 'batting_team': inning['team'], 'batter': delivery['batter'], 'bowler': delivery['bowler'], 'runs_off_bat': runs['batter'], 'extras': runs['extras'], 'total_runs': runs['total']})

            bat_df, bowl_df = get_player_summaries_single_match(data)
            all_batting.append(bat_df)
            all_bowling.append(bowl_df)

        except Exception as e:
            st.error(f"Error processing file {uploaded_file.name}: {e}")
            continue

    match_summary_df = pd.DataFrame(all_match_summaries)
    ball_by_ball_df = pd.DataFrame(all_ball_by_ball)
    market_summaries_df = pd.DataFrame(all_market_summaries)
    runs_per_over_df = pd.concat(all_runs_per_over, ignore_index=True) if all_runs_per_over else pd.DataFrame()
    stat_summary_df = pd.DataFrame(all_stat_summaries)
    
    agg_batting, agg_bowling = pd.DataFrame(), pd.DataFrame()
    if all_batting:
        full_batting_df = pd.concat(all_batting, ignore_index=True)
        if not full_batting_df.empty:
            agg_batting = full_batting_df.groupby(['player_name', 'team'])[['runs', 'balls_faced', 'fours', 'sixes']].sum().reset_index()
            if 'runs' in agg_batting.columns:
                agg_batting['strike_rate'] = (agg_batting['runs'] / agg_batting['balls_faced'].replace(0, 1) * 100).round(2)
                agg_batting = agg_batting.sort_values('runs', ascending=False)

    if all_bowling:
        full_bowling_df = pd.concat(all_bowling, ignore_index=True)
        if not full_bowling_df.empty:
            agg_bowling = full_bowling_df.groupby(['player_name', 'team'])[['runs_conceded', 'balls_bowled', 'wickets']].sum().reset_index()
            if 'wickets' in agg_bowling.columns:
                agg_bowling['overs'] = agg_bowling['balls_bowled'].apply(lambda x: f"{int(x // 6)}.{int(x % 6)}")
                agg_bowling['economy_rate'] = (agg_bowling['runs_conceded'] / (agg_bowling['balls_bowled'].replace(0, 1) / 6)).round(2)
                agg_bowling = agg_bowling.sort_values('wickets', ascending=False)

    return all_match_data, match_summary_df, ball_by_ball_df, agg_batting, agg_bowling, market_summaries_df, runs_per_over_df, stat_summary_df

# --- [CSV Analyzer Functions remain the same] ---
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
st.title("🏏 Cricket Data & Betting Market Analyzer")

st.sidebar.header("Upload Data")
if 'json_uploader_key' not in st.session_state: st.session_state.json_uploader_key = 0
if 'csv_uploader_key' not in st.session_state: st.session_state.csv_uploader_key = 1000
json_files = st.sidebar.file_uploader("Upload Cricsheet JSON match files", type=["json"], accept_multiple_files=True, key=st.session_state.json_uploader_key)
if st.sidebar.button("Clear Uploaded Files"):
    st.session_state.json_uploader_key += 1
    st.session_state.csv_uploader_key += 1
    st.rerun()

st.sidebar.header("Navigation")
main_page = st.sidebar.radio("Choose an analyzer", ["JSON Data Analyzer", "CSV Market Analyzer"])

if main_page == "JSON Data Analyzer":
    if json_files:
        raw_data, match_summary, bbb, batting_summary, bowling_summary, market_summaries_df, runs_per_over_df, stat_summary_df = process_all_files(json_files)

        st.sidebar.subheader("JSON Analyzer Views")
        json_page = st.sidebar.radio("Choose a data view", ["Match Summaries", "Aggregated Batting Stats", "Aggregated Bowling Stats", "Combined Ball-by-Ball", "Betting Market Summaries", "Runs per Over", "Statistical Summary (Binary & Totals)"])
        
        st.header(f"Analysis of {len(json_files)} Match(es)")
        st.markdown("---")

        if json_page == "Match Summaries":
            st.subheader("Detailed Cricket Match Summaries")
            st.dataframe(match_summary)
            st.download_button("Download Summaries CSV", to_csv(match_summary), "match_summaries.csv", "text/csv")
        
        elif json_page == "Aggregated Batting Stats":
            st.subheader("Aggregated Player Batting Stats Across All Matches")
            st.dataframe(batting_summary)
            st.download_button("Download Batting CSV", to_csv(batting_summary), "aggregated_batting_summary.csv", "text/csv")
        
        elif json_page == "Aggregated Bowling Stats":
            st.subheader("Aggregated Player Bowling Stats Across All Matches")
            st.dataframe(bowling_summary)
            st.download_button("Download Bowling CSV", to_csv(bowling_summary), "aggregated_bowling_summary.csv", "text/csv")
        
        elif json_page == "Combined Ball-by-Ball":
            st.subheader("Combined Ball-by-Ball Data Log")
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
                        display_dict = {k: v for k, v in match_summary_dict.items() if v not in ['N/A', 0, 'None', '']}
                        for i, (key, value) in enumerate(display_dict.items()):
                            if i % 2 == 0: col1.markdown(f"**{key}:** {value}")
                            else: col2.markdown(f"**{key}:** {value}")
                        single_match_df = pd.DataFrame([match_summary_dict])
                        st.download_button(label=f"Download Summary for {match_id}",data=to_csv(single_match_df),file_name=f"market_summary_{match_id.replace('.json','')}.csv",mime="text/csv",key=f"download_{match_id}")
            else:
                st.warning("Could not generate market summaries from the uploaded files.")
        
        elif json_page == "Runs per Over":
            st.subheader("Runs per Over Summary")
            if not runs_per_over_df.empty:
                st.download_button(label="Download All Runs per Over Data (CSV)", data=to_csv(runs_per_over_df), file_name="all_runs_per_over.csv", mime="text/csv")
                st.markdown("---")
                for match_id in runs_per_over_df['match_id'].unique():
                    with st.expander(f"**Match ID: {match_id}**"):
                        match_data = runs_per_over_df[runs_per_over_df['match_id'] == match_id]
                        inning1_data = match_data[match_data['inning'] == 1]
                        inning2_data = match_data[match_data['inning'] == 2]
                        col1, col2 = st.columns(2)
                        if not inning1_data.empty:
                            with col1:
                                st.write(f"**Inning 1: {inning1_data['team'].iloc[0]}**")
                                st.dataframe(inning1_data)
                                st.line_chart(inning1_data.rename(columns={'over': 'index'}).set_index('index')['cumulative_runs'])
                        if not inning2_data.empty:
                            with col2:
                                st.write(f"**Inning 2: {inning2_data['team'].iloc[0]}**")
                                st.dataframe(inning2_data)
                                st.line_chart(inning2_data.rename(columns={'over': 'index'}).set_index('index')['cumulative_runs'])
            else:
                st.warning("Could not generate runs per over summaries.")
        
        elif json_page == "Statistical Summary (Binary & Totals)":
            st.subheader("Statistical Summary (1=Home, 2=Away, 0=Draw)")
            st.dataframe(stat_summary_df)
            st.download_button("Download Statistical Summary CSV", to_csv(stat_summary_df), "statistical_summary.csv", "text/csv")

    else:
        st.info("Upload your Cricsheet JSON files to generate detailed match summaries, player statistics, and betting market outcomes.")

elif main_page == "CSV Market Analyzer":
    st.header("Analyze Cricket Betting Market Trends from CSV")
    st.info("Upload a CSV file (like the 'all_market_summaries.csv' generated by this app) to analyze trends across multiple matches.")
    
    csv_file = st.file_uploader("Upload Market Summary CSV", type=["csv"], key=st.session_state.csv_uploader_key)
    
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
