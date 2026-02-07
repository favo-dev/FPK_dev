
                                        continue
                                    new_r[k] = v
                                # sovrascriviamo la league con quella nuova
                                new_r["league"] = dest_league
                                # generiamo un nuovo id (UUID) per la riga inserita
                                new_r["id"] = str(uuid.uuid4())
                                insert_rows.append(new_r)

                            if not insert_rows:
                                st.info(f"No rows to insert for {table_name} after filtering.")
                                return

                            try:
                                ins = supabase.from_(table_name).insert(insert_rows).execute()
                            except Exception as e:
                                st.error(f"Exception inserting into {table_name}: {e}")
                                return

                            if getattr(ins, "error", None):
                                st.error(f"Error inserting into {table_name}: {ins.error}")
                            else:
                                inserted = ins.data or []
                                st.info(f"Copied {len(inserted)} rows into {table_name} for league '{dest_league}'.")


                        TEMPLATE_LEAGUE = "Fantamotori"
                        copy_rules_from_template("rules_mgp_new", TEMPLATE_LEAGUE, league_id)
                        copy_rules_from_template("rules_f1_new", TEMPLATE_LEAGUE, league_id)

                        try:
                            roh_row = {
                                "id": str(uuid.uuid4()),
                                "year": datetime.now().year,
                                "league": league_id
                            }
                            roh_ins = supabase.from_("roll_of_honor_new").insert(roh_row).execute()
                            if getattr(roh_ins, "error", None):
                                st.error(f"Error inserting into roll_of_honor_new: {roh_ins.error}")
                            else:
                                st.info(f"Inserted roll_of_honor_new row for year {roh_row['year']}.")
                        except Exception as e:
                            st.error(f"Exception inserting roll_of_honor_new: {e}")

                        try:
                            penalty_row = {
                                "id": str(uuid.uuid4()),
                                "uuid": user.get("UUID"),
                                "league": league_id
                            }
                            pen_ins = supabase.from_("penalty_new").insert(penalty_row).execute()
                            if getattr(pen_ins, "error", None):
                                st.error(f"Error inserting into penalty_new: {pen_ins.error}")
                            else:
                                st.info("Inserted penalty_new row for league.")
                        except Exception as e:
                            st.error(f"Exception inserting penalty_new: {e}")

                        try:
                            f1_points_row = {
                                "prim_key": str(uuid.uuid4()),
                                "id": user.get("UUID"),
                                "league": league_id
                            }
                            row_ins = supabase.from_("points_per_race_f1").insert(f1_points_row).execute()
                            if getattr(row_ins, "error", None):
                                st.error(f"Error inserting into points_per_race_f1: {row_ins.error}")
                            else:
                                st.info("Inserted points_per_race_f1 row for league.")
                        except Exception as e:
                            st.error(f"Exception inserting points_per_race_f1: {e}")

                        try:
                            mgp_points_row = {
                                "prim_key": str(uuid.uuid4()),
                                "id": user.get("UUID"),
                                "league": league_id
                            }
                            row_ins = supabase.from_("points_per_race_mgp").insert(mgp_points_row).execute()
                            if getattr(row_ins, "error", None):
                                st.error(f"Error inserting into points_per_race_mgp: {row_ins.error}")
                            else:
                                st.info("Inserted points_per_race_mgp row for league.")
                        except Exception as e:
                            st.error(f"Exception inserting points_per_race_mgp: {e}")

                        try:
                            # prepara riga per calls_f1_new
                            call_row_f1 = {
                                "id": str(uuid.uuid4()),
                                "uuid": player_uuid,
                                "league": league_id
                            }

                            cf1_ins = supabase.from_("calls_f1_new").insert([call_row_f1]).execute()
                            if getattr(cf1_ins, "error", None):
                                st.error(f"Error inserting into calls_f1_new: {cf1_ins.error}")
                            else:
                                inserted_f1 = (cf1_ins.data or [])

                            # prepara riga per calls_mgp_new (uuid diverso)
                            call_row_mgp = {
                                "id": str(uuid.uuid4()),
                                "uuid": player_uuid,
                                "league": league_id
                            }

                            cmgp_ins = supabase.from_("calls_mgp_new").insert([call_row_mgp]).execute()
                            if getattr(cmgp_ins, "error", None):
                                st.error(f"Error inserting into calls_mgp_new: {cmgp_ins.error}")
                            else:
                                inserted_mgp = (cmgp_ins.data or [])

                        except Exception as e:
                            st.error(f"Exception inserting into calls tables: {e}")

                        def create_stats_for_series(league_id, racers_table, stats_table, player_col="id", player_field_in_stats="player_id"):
                            """
                            Inserisce in stats_table una riga per ogni racer presente in racers_table con go == True.
                            - racers_table: es. "racers_f1_new" o "racers_mgp_new"
                            - stats_table: es. "league_f1_stats" o "league_mgp_stats"
                            - player_col: colonna nella tabella racers (di solito "id")
                            - player_field_in_stats: campo in stats_table dove salvare l'id del giocatore (di solito "player_id")
                            Nota: non includiamo "uuid" perchè lo genera il DB/Supabase automaticamente.
                            """
                            try:
                                racers_resp = supabase.from_(racers_table).select(player_col).eq("go", True).execute()
                                if getattr(racers_resp, "error", None):
                                    st.warning(f"Warning fetching racers from {racers_table}: {racers_resp.error}")
                                    racer_rows = []
                                else:
                                    racer_rows = racers_resp.data or []

                                player_ids = [r.get(player_col) for r in racer_rows if r.get(player_col)]

                                if player_ids:
                                    stats_rows = [{ "league_id": league_id, player_field_in_stats: pid } for pid in player_ids]
                                    insert_stats_resp = supabase.from_(stats_table).insert(stats_rows).execute()
                                    if getattr(insert_stats_resp, "error", None):
                                        st.error(f"Errore inserimento {stats_table}: {insert_stats_resp.error}")
                                    else:
                                        inserted = insert_stats_resp.data or []
                                        st.info(f"Create {len(inserted)} righe in {stats_table} per la league '{league_id}'.")
                                else:
                                    st.info(f"Nessun racer in {racers_table} con go == True trovato — nessuna riga creata in {stats_table}.")
                            except Exception as e:
                                st.error(f"Eccezione durante creazione {stats_table}: {e}")

                        # chiama la funzione per F1 (compatibile col codice esistente)
                        create_stats_for_series(league_id, "racers_f1_new", "league_f1_stats", player_col="id", player_field_in_stats="player_id")

                        # chiama la funzione per MotoGP
                        create_stats_for_series(league_id, "racers_mgp_new", "league_mgp_stats", player_col="id", player_field_in_stats="player_id")

                        # Colori HEX → RGB
                        main_color_rgb = hex_to_rgb(st.session_state.get("main_color_hex", "#00CAFF"))
                        second_color_rgb = hex_to_rgb(st.session_state.get("second_color_hex", "#FFFFFF"))

                        if main_color_rgb is None or second_color_rgb is None:
                            st.error("Errore nella conversione dei colori. Riprova.")
                        else:
                            # crea la squadra (usa nomi colonna con spazi come nel tuo DB)
                            team_inserted = build_team(
                                st.session_state.get("user"),
                                league_id,
                                team_name_val,
                                main_color_rgb,
                                second_color_rgb,
                                team_location_val,
                                foundation,
                            )

                            if team_inserted:
                                # aggiorna cronologia e nav, poi torna alla home (team)
                                hist = st.session_state.get("screen_history", [])
                                hist.append("leagues")
                                st.session_state["screen_history"] = hist
                                st.session_state["nav_selection"] = "Your team"
                                st.session_state["screen"] = "team"
                                st.session_state["selected_league"] = league_id
                                st.session_state.go = True
                                st.rerun()
                            else:
                                st.error("League created, but team creation failed.")
