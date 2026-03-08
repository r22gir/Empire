# ============================================
# EMPIRE v4.0 — DATA & FILE PATHS
# ============================================

graph TB
    subgraph ROOT["~/empire-repo/"]
        subgraph BACKEND["backend/"]
            subgraph DATA["backend/data/ — ALL RUNTIME DATA"]
                BRAIN_DIR["brain/<br/>memories.db<br/>embeddings.db"]
                MAX_DIR["max/<br/>memory.md"]
                CHATS["chats/<br/>founder/*.json<br/>telegram/*.json"]
                QUOTES["quotes/<br/>*.json, pdf/"]
                INBOX["inbox/<br/>*.json"]
                UPLOADS["uploads/<br/>images/ docs/"]
                LOGS["logs/<br/>YYYY-MM-DD/"]
                PRES["presentations/<br/>*.pdf"]
                EMPIRE_DB["empire.db<br/>Tasks, Desks"]
            end
            VENV["venv/<br/>Python 3.12"]
            APP["app/<br/>FastAPI Code"]
            ENV[".env<br/>API Keys"]
        end

        subgraph FRONTS["Frontend Apps"]
            FD_DIR["founder_dashboard/<br/>.env.local"]
            EA_DIR["empire-app/"]
            WF_DIR["workroomforge/<br/>.env.local"]
            LF_DIR["luxeforge_web/"]
        end

        subgraph DOCS["docs/"]
            ARCHIVE["CHAT_ARCHIVE/"]
            SALVAGED["salvaged/"]
        end

        SCRIPTS["start-empire.sh<br/>stop-empire.sh"]
        VERSION["VERSION → 4.0"]
        CLAUDEMD["CLAUDE.md"]
    end
