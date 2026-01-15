#!/bin/bash
set -euo pipefail

PROJECT_DIR="${HOME}/inkognito"
BRANCH="master"
VENV_DIR="${PROJECT_DIR}/venv"

MAKE_TARGET="run-https"

PID_FILE="/tmp/inkognito_server.pid"
LOGFILE="${PROJECT_DIR}/logs/inkognito_server.log"
SSLKEYFILE="${PROJECT_DIR}/certs/key.pem"
SSLCERTFILE="${PROJECT_DIR}/certs/cert.pem"


LOCKDIR="/tmp/inkognito_deploy_lock"
if ! mkdir "${LOCKDIR}" 2>/dev/null; then
    echo "Another deployment is in progress. Exiting."
    exit 1
fi

trap 'rm -rf "${LOCKDIR}"' EXIT

ts() {
    date +"[%Y-%m-%d %H:%M:%S] $*"
}
log() {
    echo "$(ts) $*" | tee -a "$LOGFILE";
}

cd "$PROJECT_DIR"

if [[ ! -f "$PROJECT_DIR/Makefile" && ! -f "$PROJECT_DIR/makefile" ]]; then
  log "ERRORE: Makefile non trovato in $PROJECT_DIR."
  exit 1
fi
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  log "ERRORE: venv non trovato: $VENV_DIR (manca $VENV_DIR/bin/python)."
  exit 1
fi

git fetch origin "$BRANCH" || { log "ERRORE: git fetch fallito."; exit 1; }

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse origin/"$BRANCH")"

if [[ "$LOCAL" == "$REMOTE" ]]; then
    log "Nessun aggiornamento trovato. Uscita."
    exit 0
fi

log "Aggiornamenti trovati: LOCAL=$LOCAL, REMOTE=$REMOTE. Avvio del deploy..."

if [[ -f "$PID_FILE" ]]; then
    PID="$(cat "$PID_FILE" 2>/dev/null || true)"
    log "Trovato PID del server in esecuzione: $PID"
    if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
        log "Arresto del server in esecuzione (PID=$PID)..."
        kill -TERM "$PID" 2>/dev/null || { log "ERRORE: Impossibile terminare il processo PID=$PID."; exit 1; }
        sleep 2
    else
        log "Nessun server in esecuzione trovato con PID=$PID. Continuo..."
    fi
    rm -f "$PID_FILE"
fi

log "git pull --ff-only origin $BRANCH..."

git pull --ff-only origin "$BRANCH" | tee -a "$LOGFILE"

if [[ ! -f "$SSLKEYFILE" || ! -f "$SSLCERTFILE" ]]; then
  log "ERRORE: File di certificato SSL non trovati: $SSLKEYFILE o $SSLCERTFILE. Creazione di nuovi"
  "${PROJECT_DIR}/certs/generate_certificate.sh" || { log "ERRORE: generazione del certificato SSL fallita."; exit 1; }
fi

log "Attivazione del venv in $VENV_DIR..."

export PATH="$VENV_DIR/bin:$PATH"
export VIRTUAL_ENV="$VENV_DIR"

nohup make "$MAKE_TARGET" SSLKEYFILE="$SSLKEYFILE" SSLCERTFILE="$SSLCERTFILE" >> "$LOGFILE" 2>&1 &

NEW_PID="$!"

echo "$NEW_PID" > "$PID_FILE"
log "Server avviato con PID=$NEW_PID (target=$MAKE_TARGET)."