import streamlit as st
from st_supabase_connection import SupabaseConnection
from streamlit_cookies_controller import CookieController
cookies = CookieController()


conn = st.connection("supabase",type=SupabaseConnection)

st.write(st.session_state)
if "game_id" not in st.query_params:
    new_game_name = st.text_input("Name of new game", "my game")
    create_game = st.button("Create new game")
    if create_game:
        resp = conn.table("games").upsert({"name": new_game_name}).execute()
        game_created = resp.data[0]
        uid = game_created["id"]
        pwd = game_created["password"]
        st.query_params["game_id"] = uid
        st.session_state["game_password"] = pwd
        cookies.set("game_password",pwd)
        st.write(f"Game ID: {uid}")
        st.rerun()
    join_game = st.text_input("Game ID to join")
    if st.button("Join game as user"):
        st.query_params["game_id"] = join_game
        st.rerun()
    join_game_pwd = st.text_input("Game Password to join as admin")
    if st.button("Join game as admin"):
        game = conn.table("games").select("*").eq("password",join_game_pwd).execute().data[0]
        st.query_params["game_id"] = game["id"]
        cookies.set("game_password",join_game_pwd)
        st.rerun()
else:
    game = conn.table("games").select("*").eq("id",st.query_params["game_id"]).execute().data[0]
    teams = conn.table("teams").select("*").eq("game",game["id"]).execute().data
    #st.write(game)
    st.write(f"Game ID: {st.query_params['game_id']}")
    pwd_cookie = cookies.get("game_password")
    is_admin = pwd_cookie == game["password"]
    if pwd_cookie is not None and pwd_cookie != game["password"]:
        cookies.remove("game_password")
        st.rerun()
    if is_admin:
        st.title(f"Admin in game {game['name']}")
        st.write("Game password: ")
        st.code(cookies.get("game_password"),language="md")
        
        new_team_name = st.text_input("New team name")
        if st.button("Create new team"):
            resp = conn.table("teams").upsert({"name": new_team_name, "game": game["id"]}).execute()
            st.rerun()
        st.dataframe(teams, use_container_width=True)
        team_to_delete = st.selectbox("Team to delete", [team["name"] for team in teams])
        if st.button("Delete team"):
            team_id = [team["id"] for team in teams if team["name"] == team_to_delete][0]
            conn.table("teams").delete().eq("id",team_id).execute()
            st.rerun()
        
        
        
    
    

