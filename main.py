import streamlit as st
from sqlalchemy import create_engine, text
import pandas as pd
import os
from dotenv import load_dotenv

# PostgreSQL bağlantısı
# DB_URL = "postgresql://ata:dartligi@postgres:5432/otuz_dart_lig"
load_dotenv()
DB_URL = os.getenv("DB_URL")
engine = create_engine(DB_URL)


def delete_data_in_tables():
    with engine.connect() as conn:
        conn.execute(text('''
                    DROP TABLE players_501 cascade;
                    DROP TABLE players_cricket cascade;
                    DROP TABLE matches_501  cascade;
                    DROP TABLE matches_cricket  cascade;
                    DROP TABLE scores_501 cascade;
                    DROP TABLE scores_cricket  cascade;
                    '''
                    ))
        conn.commit()
        

# Veritabanı tablolarını oluştur
def create_tables():
    with engine.connect() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS players_501 (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS players_cricket (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL
            );

            CREATE TABLE IF NOT EXISTS matches_501 (
                id SERIAL PRIMARY KEY,
                player1_id INT REFERENCES players_501(id),
                player2_id INT REFERENCES players_501(id),
                match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS matches_cricket (
                id SERIAL PRIMARY KEY,
                player1_id INT REFERENCES players_cricket(id),
                player2_id INT REFERENCES players_cricket(id),
                match_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS scores_501 (
                id SERIAL PRIMARY KEY,
                match_id INT REFERENCES matches_501(id),
                player_id INT REFERENCES players_501(id),
                score INT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scores_cricket (
                id SERIAL PRIMARY KEY,
                match_id INT REFERENCES matches_cricket(id),
                player_id INT REFERENCES players_cricket(id),
                score INT NOT NULL
            );
        '''))
        conn.commit()


# Oyuncu ekleme fonksiyonu
def add_player(name, game_type):
    table = "players_501" if game_type == "501" else "players_cricket"
    with engine.connect() as conn:
        trans = conn.begin()
        conn.execute(text(f"INSERT INTO {table} (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"), {"name": name})
        trans.commit()


# Oyuncuları getir
def get_players(game_type):
    table = "players_501" if game_type == "501" else "players_cricket"
    with engine.connect() as conn:
        players = pd.read_sql(f"SELECT * FROM {table}", con=conn)
    return players if not players.empty else pd.DataFrame(columns=["id", "name"])


# Maç ekleme
def add_match(player1_id, player2_id, player1_score, player2_score, game_type):
    match_table = "matches_501" if game_type == "501" else "matches_cricket"
    score_table = "scores_501" if game_type == "501" else "scores_cricket"
    with engine.connect() as conn:
        trans = conn.begin()
        result = conn.execute(
            text(f"INSERT INTO {match_table} (player1_id, player2_id) VALUES (:player1, :player2) RETURNING id"),
            {"player1": player1_id, "player2": player2_id})
        match_id = result.fetchone()[0]

        # Skorları ekleyelim
        conn.execute(text(
            f"INSERT INTO {score_table} (match_id, player_id, score) VALUES (:match_id, :player1, :score1), (:match_id, :player2, :score2)"),
                     {"match_id": match_id, "player1": player1_id, "score1": player1_score, "player2": player2_id,
                      "score2": player2_score})
        trans.commit()
        return match_id


# Puan tablosunu getir
def get_leaderboard(game_type):
    score_table = "scores_501" if game_type == "501" else "scores_cricket"
    player_table = "players_501" if game_type == "501" else "players_cricket"
    query = text(f"""
    WITH match_scores AS (
        SELECT s.match_id, s.player_id, s.score,
               MAX(s.score) OVER (PARTITION BY s.match_id) AS max_score,
               MIN(s.score) OVER (PARTITION BY s.match_id) AS min_score
        FROM {score_table} s
    )
    SELECT p.name, 
           COALESCE(COUNT(DISTINCT s.match_id), 0) AS matches_played,
           COALESCE(SUM(CASE WHEN s.match_id IS NULL THEN 0 WHEN s.score = s.max_score THEN 3 ELSE 1 END), 0) AS total_points,

           COALESCE(SUM(s.score), 0) AS sets_won,
           COALESCE(SUM(CASE WHEN s.score = s.min_score THEN s.max_score ELSE s.min_score END), 0) AS sets_lost
    FROM {player_table} p
    LEFT JOIN match_scores s ON p.id = s.player_id
    GROUP BY p.name
    ORDER BY total_points DESC;
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, con=conn)


# Streamlit UI
def main():
    st.title("🎯 Dart Ligi Yönetimi")
    # delete_data_in_tables()
    create_tables()

    game_type = st.sidebar.radio("Oyun Türü Seçin", ["501", "Cricket"])
    menu = st.sidebar.radio("Menü",
                            ["Oyuncu Ekle", "Maç Kaydet", "Maç Sonuçları", "Puan Tablosu", "Maç Skoru Güncelle"])


    if menu == "Oyuncu Ekle":
        st.subheader("Oyuncu Ekle")
        player_name = st.text_input("Oyuncu Adı")
        if st.button("Ekle"):
            add_player(player_name, game_type)
            st.success(f"{player_name} eklendi!")

    elif menu == "Maç Kaydet":
        st.subheader("Maç Kaydet")
        players = get_players(game_type)
        player_options = players.set_index("id")["name"].to_dict()
        
        # player_options = {k: player_options[k] for k in list(player_options)[:2]}


        if len(player_options) >= 2:
            player1 = st.selectbox("Oyuncu 1", options=player_options.keys(), format_func=lambda x: player_options[x])
            player2 = st.selectbox("Oyuncu 2", options=player_options.keys(), format_func=lambda x: player_options[x])
            player1_score = st.number_input("Oyuncu 1 Skoru", min_value=0, step=1)
            player2_score = st.number_input("Oyuncu 2 Skoru", min_value=0, step=1)

            if st.button("Maçı Kaydet"):
                match_id = add_match(player1, player2, player1_score, player2_score, game_type)
                st.success(f"Maç kaydedildi! (ID: {match_id})")
        else:
            st.warning("En az 2 oyuncu ekleyin!")
    elif menu == "Maç Sonuçları":
        st.subheader("📊 Maç Sonuçları")
        match_table = "matches_501" if game_type == "501" else "matches_cricket"
        player_table = "players_501" if game_type == "501" else "players_cricket"
        score_table = "scores_501" if game_type == "501" else "scores_cricket"

        players = get_players(game_type)
        player_options = {None: "Tüm Oyuncular"}
        player_options.update(players.set_index("id")["name"].to_dict())
        selected_player = st.selectbox("Oyuncu Seç", options=player_options.keys(),
                                       format_func=lambda x: player_options[x])

        query = text(f"""
            SELECT m.id AS match_id, p1.name AS player1, p2.name AS player2, 
                   s1.score AS player1_score, s2.score AS player2_score, m.match_date 
            FROM {match_table} m
            JOIN {player_table} p1 ON m.player1_id = p1.id
            JOIN {player_table} p2 ON m.player2_id = p2.id
            JOIN {score_table} s1 ON m.id = s1.match_id AND s1.player_id = p1.id
            JOIN {score_table} s2 ON m.id = s2.match_id AND s2.player_id = p2.id
            """
                     )
        if selected_player:
            query = text(query.text + " WHERE m.player1_id = :selected_player OR m.player2_id = :selected_player")

        match_results = pd.read_sql(query, con=engine.connect(), params={"selected_player": selected_player})
        st.dataframe(match_results)

    elif menu == "Puan Tablosu":
        st.subheader("🏆 Puan Tablosu")
        leaderboard = get_leaderboard(game_type)
        st.dataframe(leaderboard)


if __name__ == "__main__":
    main()
