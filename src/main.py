import streamlit as st
from st_supabase_connection import SupabaseConnection
from random import shuffle


conn = st.connection("supabase",type=SupabaseConnection)

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
        st.query_params["game_password"] = pwd
        st.write(f"Game ID: {uid}")
        st.rerun()
    team_password = st.text_input("Team password to join as player")
    if st.button("Join a team"):
        games = conn.table("teams").select("game").eq("password",team_password).execute().data
        if len(games) != 1:
            st.write("Invalid password")
        else:
            st.query_params["game_id"] = games[0]["game"]
            st.query_params["team_password"] = team_password
            st.rerun()
    join_game_pwd = st.text_input("Game Password to join as admin")
    if st.button("Join game as admin"):
        game = conn.table("games").select("*").eq("password",join_game_pwd).execute().data[0]
        st.query_params["game_id"] = game["id"]
        st.query_params["game_password"] = join_game_pwd
        st.rerun()
else:
    if st.button("logout"):
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
    game = conn.table("games").select("*").eq("id",st.query_params["game_id"]).execute().data[0]
    teams = conn.table("teams").select("*").eq("game",game["id"]).execute().data
    #st.write(game)
    st.write(f"Game ID: {st.query_params['game_id']}")
    is_admin = False
    if "game_password" in st.query_params:
        if st.query_params["game_password"] == game["password"]:
            is_admin = True
        else:
            del st.query_params["game_password"]
            st.rerun()
    if is_admin:
        st.title(f"Admin in game {game['name']}")
        st.write("Game password: ")
        st.code(st.query_params["game_password"],language="md")
        
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
        phases = ["preparation","generation","discrimination","done"]
        current_phase_index = phases.index(game["phase"])
        game_phase = st.selectbox("Game phase",["preparation","generation","discrimination","done"],index=current_phase_index)
        if st.button("Change game phase"):
            conn.table("games").update({"phase": game_phase}).eq("id",game["id"]).execute()
            st.rerun()
        if game["phase"] == "preparation":
            st.header("Prepare dataset")
            reals = conn.table("reals").select("id,content,is_training_sample").eq("game",game["id"]).execute().data
            st.dataframe(reals, use_container_width=True)
            
            new_sample = st.text_input("New sample to add")
            if st.button("Add new sample"):
                conn.table("reals").upsert({"content": new_sample, "game": game["id"]}).execute()
                st.rerun()
            sample_to_delete = st.selectbox("Sample to delete", [real["content"] for real in reals])
            if st.button("Delete sample"):
                sample_id = [real["id"] for real in reals if real["content"] == sample_to_delete][0]
                conn.table("reals").delete().eq("id",sample_id).execute()
                st.rerun()
            num_training_samples = st.number_input("Number of training samples",min_value=0,max_value=len(reals))
            if st.button("Sample training samples"):
                reals_ids = [real["id"] for real in reals]
                shuffle(reals_ids)
                training_samples = reals_ids[:num_training_samples]
                for real in reals:
                    sid = real["id"]
                    is_training_sample = sid in training_samples
                    conn.table("reals").update({"is_training_sample": is_training_sample}).eq("id",sid).execute()
                st.rerun()
            
    if "team_password" in st.query_params:
        team = conn.table("teams").select("*").eq("password",st.query_params["team_password"]).execute().data[0]
        st.title(f"{team["name"]} in game {game['name']}")
        st.write("Team password: ")
        st.code(st.query_params["team_password"],language="md")
        if game["phase"] == "generation":
            st.header("Generation phase")
            st.header("Training samples")
            training_samples = conn.table("reals").select("content").eq("game",game["id"]).eq("is_training_sample",True).execute().data
            st.dataframe(training_samples, use_container_width=True)
            fake_sample= st.text_input("Fake sample to create")
            if st.button("Create fake sample"):
                conn.table("fakes").upsert({"content": fake_sample, "team": team["id"]}).execute()
                st.rerun()
            fake_samples = conn.table("fakes").select("id,content").eq("team",team["id"]).execute().data
            st.dataframe(fake_samples, use_container_width=True)
            to_delete = st.selectbox("Fake sample to delete", [fake["content"] for fake in fake_samples])
            if st.button("Delete fake sample"):
                fake_id = [fake["id"] for fake in fake_samples if fake["content"] == to_delete][0]
                conn.table("fakes").delete().eq("id",fake_id).execute()
                st.rerun()
        
        if game["phase"] == "discrimination":
            st.header("Discrimination phase")
            classifications = conn.table("classifications").select("sample_id,isreal").eq("team",team["id"]).execute().data
            st.dataframe(classifications, use_container_width=True)
            reals = conn.table("reals").select("id,content").eq("game",game["id"]).eq("is_training_sample",False).execute().data
            other_teams = conn.table("teams").select("*").eq("game",game["id"]).neq("id",team["id"]).execute().data
            fakes = []
            for other_team in other_teams:
                fakes += conn.table("fakes").select("id,content").eq("team",other_team["id"]).execute().data
            def get_classification(sample_id):
                for classification in classifications:
                    if classification["sample_id"] == sample_id:
                        return classification["isreal"]
                return False
            def has_classification(sample_id):
                for classification in classifications:
                    if classification["sample_id"] == sample_id:
                        return True
                return False
            reals = [{'id': real['id'], 'content': real['content'], 'isreal': get_classification(real["id"]), "classification": True} for real in reals]
            fakes = [{'id': fake['id'], 'content': fake['content'], 'isreal': get_classification(fake["id"]), "classification": False} for fake in fakes]
            all_samples = reals + fakes
            all_samples = sorted(all_samples, key=lambda sample: sample["content"])
            
            for sample in all_samples:
                classification_id = 1 if sample["isreal"] else 0
                
                col1, col2, col3 = st.columns([4, 1, 1])
                with col1:
                    st.write(sample["content"])
                with col2:
                    classification = st.selectbox("classification",["fake","real"],index=classification_id,key=f"cb_{sample["id"]}",label_visibility="collapsed")
                with col3:
                    submit_button=st.button("Submit", key=sample["id"])
                if submit_button:
                    if has_classification(sample["id"]):
                        conn.table("classifications").update({"isreal": classification == "real"}).eq("sample_id", sample["id"]).execute()
                    else:
                        conn.table("classifications").insert({"sample_id": sample["id"], "isreal": classification == "real", "team": team["id"]}).execute()
                    st.rerun()

    

