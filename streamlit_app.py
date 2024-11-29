import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime
import hashlib

# Initialize Supabase client
SUPABASE_URL = "https://yvrxmcdeisyfzhcrizef.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inl2cnhtY2RlaXN5ZnpoY3JpemVmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzI4ODQ3ODgsImV4cCI6MjA0ODQ2MDc4OH0.vU4-t6_5JAbVfkcehc9n0nPyGgStTy06trfRSC2KIiA"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Page configuration
st.set_page_config(page_title="Golf Scoring App", layout="wide")

# Session state initialization
if 'current_hole' not in st.session_state:
    st.session_state.current_hole = 1
if 'player' not in st.session_state:
    st.session_state.player = None

def hash_password(password):
    """Hash a password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def login():
    """Player login or registration"""
    st.title("Player Login")

    with st.form("login_form"):
        player_name = st.text_input("Enter your name")
        password = st.text_input("Enter your password", type='password')
        team_name = st.text_input("Enter your team name", disabled=player_name == 'admin')
        submit = st.form_submit_button("Login/Register")

        if submit:
            if player_name and password:
                if player_name == 'admin':
                    # Replace with your actual hashed admin password
                    admin_password_hash = hash_password('admin')
                    password_hash = hash_password(password)
                    
                    if password_hash == admin_password_hash:
                        st.session_state.player = {'name': 'admin', 'is_admin': True}
                        st.success("Admin logged in!")
                        st.rerun()
                    else:
                        st.error("Incorrect admin password.")
                else:
                    if team_name:
                        # Existing player login/registration logic
                        player_response = supabase.table('players')\
                            .select('*').eq('name', player_name).execute()
                        if player_response.data:
                            # Player exists
                            st.session_state.player = player_response.data[0]
                            # Fetch team information
                            team_response = supabase.table('teams')\
                                .select('*').eq('id', st.session_state.player['team_id']).execute()
                            if team_response.data:
                                st.session_state.player['team'] = team_response.data[0]
                            st.success(f"Welcome back, {player_name}!")
                            st.rerun()
                        else:
                            # Register new player
                            team_response = supabase.table('teams')\
                                .select('*').eq('name', team_name).execute()
                            if team_response.data:
                                team_id = team_response.data[0]['id']
                            else:
                                # Create new team
                                team_creation = supabase.table('teams')\
                                    .insert({'name': team_name}).execute()
                                team_id = team_creation.data[0]['id']

                            player_creation = supabase.table('players').insert({
                                'name': player_name,
                                'team_id': team_id
                            }).execute()
                            st.session_state.player = player_creation.data[0]
                            # Fetch team information
                            st.session_state.player['team'] = {'id': team_id, 'name': team_name}
                            st.success(f"Player {player_name} registered and added to team {team_name}!")
                            st.rerun()
                    else:
                        st.error("Please enter your team name.")
            else:
                st.error("Please enter your name and password.")

def manage_players():
    """Admin interface to manage players"""
    st.header("Manage Players")

    # Fetch all players with their team information
    response = supabase.table('players').select('id, name, team_id, teams(id, name)').execute()
    players = response.data

    if players:
        # Create a DataFrame for display
        df = pd.DataFrame(players)
        df['Team'] = df['teams'].apply(lambda x: x['name'] if x else 'No Team')
        st.dataframe(df[['id', 'name', 'Team']])

        # Select a player to edit
        selected_player = st.selectbox(
            "Select a player to edit",
            players,
            format_func=lambda x: x['name']
        )

        if selected_player:
            st.subheader(f"Editing Player: {selected_player['name']}")

            # Fetch teams for team assignment
            team_response = supabase.table('teams').select('id, name').execute()
            teams = team_response.data
            team_options = {team['id']: team['name'] for team in teams}

            # Current team selection
            current_team_id = selected_player['team_id']
            new_team_id = st.selectbox(
                "Assign new team",
                options=team_options.keys(),
                format_func=lambda x: team_options[x],
                index=list(team_options.keys()).index(current_team_id) if current_team_id else 0
            )

            # Update team button
            if st.button("Update Team"):
                supabase.table('players').update({'team_id': new_team_id})\
                    .eq('id', selected_player['id']).execute()
                st.success("Player's team updated!")
                st.rerun()

            # Delete player button
            if st.button("Delete Player"):
                supabase.table('players').delete().eq('id', selected_player['id']).execute()
                st.success("Player deleted!")
                st.rerun()
    else:
        st.info("No players found.")

def manage_teams():
    """Admin interface to manage teams"""
    st.header("Manage Teams")

    # Fetch all teams
    response = supabase.table('teams').select('id, name').execute()
    teams = response.data

    if teams:
        df = pd.DataFrame(teams)
        st.dataframe(df[['id', 'name']])

        # Select a team to delete
        selected_team = st.selectbox(
            "Select a team to delete",
            teams,
            format_func=lambda x: x['name']
        )

        if selected_team:
            st.subheader(f"Deleting Team: {selected_team['name']}")

            # Confirm deletion
            if st.button("Delete Team"):
                # Check if there are players in the team
                player_check = supabase.table('players').select('id').eq('team_id', selected_team['id']).execute()
                if player_check.data:
                    st.error("Cannot delete a team that has players assigned. Reassign or delete players first.")
                else:
                    supabase.table('teams').delete().eq('id', selected_team['id']).execute()
                    st.success("Team deleted!")
                    st.rerun()
    else:
        st.info("No teams found.")

def admin_interface():
    """Admin dashboard"""
    st.title("Admin Dashboard")

    st.sidebar.title("Admin Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["Manage Players", "Manage Teams"]
    )

    if page == "Manage Players":
        manage_players()
    elif page == "Manage Teams":
        manage_teams()

    if st.sidebar.button("Logout"):
        st.session_state.player = None
        st.rerun()

def show_leaderboard():
    """Display the leaderboard"""
    st.header("Leaderboard")

    try:
        # Fetch scores with related player and team data
        response = supabase.table('scores').select(
            'score, players(name, team_id, teams(name))'
        ).execute()
        scores_data = response.data

        if scores_data:
            df = pd.DataFrame(scores_data)
            df['Player'] = df['players'].apply(lambda x: x['name'])
            df['Team'] = df['players'].apply(lambda x: x['teams']['name'])
            df['Score'] = df['score']

            # Calculate total scores per player
            player_totals = df.groupby(['Player', 'Team'])['Score'].sum().reset_index()

            st.subheader("Individual Leaderboard")
            st.dataframe(player_totals.sort_values('Score'))

            # Calculate total scores per team
            team_totals = player_totals.groupby('Team')['Score'].sum().reset_index()
            st.subheader("Team Leaderboard")
            st.dataframe(team_totals.sort_values('Score'))
        else:
            st.info("No scores recorded yet!")
    except Exception as e:
        st.error(f"Error fetching leaderboard: {str(e)}")

def show_current_hole():
    """Allow players to submit their score for the current hole"""
    st.header(f"Hole {st.session_state.current_hole}")

    try:
        # Fetch hole rule
        response = supabase.table('hole_rules')\
            .select("*")\
            .eq('hole_number', st.session_state.current_hole)\
            .execute()

        if response.data:
            st.subheader("Rule for this hole:")
            st.write(response.data[0]['rule_description'])

        # Score input section
        st.subheader("Enter Your Score")

        with st.form(f"hole_{st.session_state.current_hole}_score"):
            score = st.number_input(
                f"Your score for Hole {st.session_state.current_hole}",
                min_value=1,
                max_value=20,
                value=1
            )
            submit = st.form_submit_button("Submit Score")

            if submit:
                try:
                    player_id = st.session_state.player['id']
                    # Check if score already exists
                    existing_score = supabase.table('scores')\
                        .select("*")\
                        .eq('player_id', player_id)\
                        .eq('hole_number', st.session_state.current_hole)\
                        .execute()

                    if existing_score.data:
                        # Update existing score
                        supabase.table('scores')\
                            .update({'score': score})\
                            .eq('player_id', player_id)\
                            .eq('hole_number', st.session_state.current_hole)\
                            .execute()
                    else:
                        # Insert new score
                        supabase.table('scores').insert({
                            'player_id': player_id,
                            'hole_number': st.session_state.current_hole,
                            'score': score,
                            'date_recorded': datetime.utcnow().isoformat()
                        }).execute()
                    st.success("Your score has been updated!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error updating your score: {str(e)}")

        # Display current hole scores for the player's team
        st.subheader("Team Scores for Current Hole")
        scores_response = supabase.table('scores')\
            .select('score, players(name, team_id, teams(name))')\
            .eq('hole_number', st.session_state.current_hole)\
            .execute()

        if scores_response.data:
            scores_df = pd.DataFrame(scores_response.data)
            scores_df['player_name'] = scores_df['players'].apply(lambda x: x['name'])
            scores_df['team_name'] = scores_df['players'].apply(lambda x: x['teams']['name'])
            scores_df['score'] = scores_df['score']

            # Filter for the player's team
            player_team_name = st.session_state.player['team']['name']
            team_scores = scores_df[scores_df['team_name'] == player_team_name]
            display_df = team_scores[['player_name', 'score']].rename(
                columns={'player_name': 'Player', 'score': 'Score'}
            )
            st.dataframe(display_df)
        else:
            st.info("No scores recorded for this hole yet!")

        # Navigation buttons
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Previous Hole") and st.session_state.current_hole > 1:
                st.session_state.current_hole -= 1
                st.rerun()
        with col3:
            if st.button("Next Hole") and st.session_state.current_hole < 18:
                st.session_state.current_hole += 1
                st.rerun()

    except Exception as e:
        st.error(f"Error loading hole information: {str(e)}")

def main():
    """Main app function for players and admin"""
    if st.session_state.player is None:
        login()
    else:
        if st.session_state.player.get('is_admin', False):
            # Admin interface
            admin_interface()
        else:
            # Player interface
            st.sidebar.title(f"Welcome, {st.session_state.player['name']}")
            page = st.sidebar.radio(
                "Go to",
                ["Leaderboard", "Current Hole"]
            )

            # Page routing
            if page == "Leaderboard":
                show_leaderboard()
            elif page == "Current Hole":
                show_current_hole()

            if st.sidebar.button("Logout"):
                st.session_state.player = None
                st.rerun()

if __name__ == "__main__":
    main()