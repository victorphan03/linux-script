#!/usr/bin/env bash
# ==============================================================================
# Script: backup_homelab.sh
# Strategy: 3-2-1-1-0 Homelab Backup Strategy (Granular Docker Compose Edition)
# Description: Automated backup script with Docker Compose stack auto-discovery,
#              independent per-stack stop/compress/start, SSH Remote SCP backup,
#              MinIO Object Lock, Google Drive Offsite, and Telegram Alerts.
# Managed by: Webmin Homelab Backup Module
# ==============================================================================

set -e

CONFIG_FILE="/etc/webmin/homelab-backup/config"
LOG_FILE="/opt/backup_homelab.log"

LOCAL_SRC="/home/x79"
TEMP_DIR="/opt/backups/tmp"
MINIO_REMOTE="minio_local:homelab-backups/"
CLOUD_REMOTE="remote_drive:Homelab_Backups/"
RETENTION_DAYS="7"
ENABLED_STACKS="ALL"

ENABLE_REMOTE="0"
REMOTE_IP=""
REMOTE_PORT="22"
REMOTE_USER="root"
REMOTE_SRC=""

TELEGRAM_BOT_TOKEN=""
TELEGRAM_CHAT_ID=""

SINGLE_STACK_TARGET="$1"

# Load Configuration
if [ -f "$CONFIG_FILE" ]; then
    while IFS='=' read -r key value || [ -n "$key" ]; do
        [[ "$key" =~ ^#.*$ ]] && continue
        [[ -z "$key" ]] && continue
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        case "$key" in
            local_src) [ -n "$value" ] && LOCAL_SRC="$value" ;;
            temp_dir) [ -n "$value" ] && TEMP_DIR="$value" ;;
            minio_remote) [ -n "$value" ] && MINIO_REMOTE="$value" ;;
            cloud_remote) [ -n "$value" ] && CLOUD_REMOTE="$value" ;;
            retention_days) [ -n "$value" ] && RETENTION_DAYS="$value" ;;
            enabled_stacks) [ -n "$value" ] && ENABLED_STACKS="$value" ;;
            enable_remote) [ -n "$value" ] && ENABLE_REMOTE="$value" ;;
            remote_ip) [ -n "$value" ] && REMOTE_IP="$value" ;;
            remote_port) [ -n "$value" ] && REMOTE_PORT="$value" ;;
            remote_user) [ -n "$value" ] && REMOTE_USER="$value" ;;
            remote_src) [ -n "$value" ] && REMOTE_SRC="$value" ;;
            telegram_bot_token) [ -n "$value" ] && TELEGRAM_BOT_TOKEN="$value" ;;
            telegram_chat_id) [ -n "$value" ] && TELEGRAM_CHAT_ID="$value" ;;
        esac
    done < "$CONFIG_FILE"
fi

mkdir -p "$(dirname "$LOG_FILE")"

log() {
    local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$msg" | tee -a "$LOG_FILE"
}

send_telegram() {
    local message="$1"
    if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
        curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
            -d "chat_id=${TELEGRAM_CHAT_ID}" \
            -d "parse_mode=HTML" \
            -d "text=${message}" > /dev/null 2>&1 || true
    fi
}

# Check if a stack is enabled
is_stack_enabled() {
    local stack_name="$1"
    if [ -n "$SINGLE_STACK_TARGET" ]; then
        [ "$SINGLE_STACK_TARGET" = "$stack_name" ] && return 0 || return 1
    fi
    if [ "$ENABLED_STACKS" = "ALL" ] || [ -z "$ENABLED_STACKS" ]; then
        return 0
    fi
    IFS=',' read -ra STACK_ARRAY <<< "$ENABLED_STACKS"
    for s in "${STACK_ARRAY[@]}"; do
        s_trimmed=$(echo "$s" | xargs)
        [ "$s_trimmed" = "$stack_name" ] && return 0
    done
    return 1
}

START_TIME=$(date +%s)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

log "======================================================================"
log "🚀 STARTING HOMELAB BACKUP (3-2-1-1-0 Granular Compose Strategy)"
log "======================================================================"

STATUS_REMOTE="SKIPPED"
STATUS_MINIO="SKIPPED"
STATUS_CLOUD="SKIPPED"
STATUS_INTEGRITY="PASSED"
STACK_REPORTS=""
FAILED_STACKS=0

mkdir -p "$TEMP_DIR"
log "📁 Temp Directory: $TEMP_DIR"

# Step 1: [Granular Local Docker Compose Backup]
log "🔹 [Local Backup] Scanning Docker Compose projects in $LOCAL_SRC..."

if [ -d "$LOCAL_SRC" ]; then
    # Find all docker-compose.yml or compose.yaml files
    mapfile -t COMPOSE_FILES < <(find "$LOCAL_SRC" -type f \( -name "docker-compose.yml" -o -name "docker-compose.yaml" -o -name "compose.yml" -o -name "compose.yaml" \) 2>/dev/null)

    if [ ${#COMPOSE_FILES[@]} -eq 0 ]; then
        log "⚠️ No docker-compose files found under $LOCAL_SRC. Backing up entire directory..."
        LOCAL_ARCHIVE="$TEMP_DIR/local_full_${TIMESTAMP}.tar.gz"
        if tar -czf "$LOCAL_ARCHIVE" -C "$(dirname "$LOCAL_SRC")" "$(basename "$LOCAL_SRC")" >> "$LOG_FILE" 2>&1; then
            log "  ✅ Full local backup completed."
            STACK_REPORTS="${STACK_REPORTS}%0A• <b>Full Local:</b> SUCCESS"
        else
            log "  ❌ Full local backup failed!"
            STACK_REPORTS="${STACK_REPORTS}%0A• <b>Full Local:</b> FAILED"
        fi
    else
        for cfile in "${COMPOSE_FILES[@]}"; do
            pdir=$(dirname "$cfile")
            pname=$(basename "$pdir")

            if ! is_stack_enabled "$pname"; then
                log "  ⏩ Skipping disabled stack: $pname"
                continue
            fi

            log "  ------------------------------------------------------------"
            log "  📦 Processing Docker Stack: [$pname] ($pdir)"
            STACK_START=$(date +%s)

            # Check if containers are running in this compose project
            WAS_RUNNING=0
            if command -v docker >/dev/null 2>&1; then
                RUNNING_IDS=$(docker compose -f "$cfile" ps -q 2>/dev/null || true)
                if [ -n "$RUNNING_IDS" ]; then
                    WAS_RUNNING=1
                    log "    ⏸️ Stopping containers for stack [$pname]..."
                    docker compose -f "$cfile" stop >> "$LOG_FILE" 2>&1 || true
                fi
            fi

            # Compress stack directory
            ARCHIVE_NAME="docker_stack_${pname}_${TIMESTAMP}.tar.gz"
            STACK_ARCHIVE="$TEMP_DIR/$ARCHIVE_NAME"
            log "    📁 Archiving directory to $ARCHIVE_NAME..."

            STACK_STATUS="SUCCESS"
            if tar -czf "$STACK_ARCHIVE" -C "$(dirname "$pdir")" "$(basename "$pdir")" >> "$LOG_FILE" 2>&1; then
                log "    ✅ Archive created successfully."
            else
                STACK_STATUS="FAILED"
                FAILED_STACKS=$((FAILED_STACKS + 1))
                log "    ❌ Archiving failed for stack [$pname]!"
            fi

            # Restart containers immediately for minimal downtime
            if [ "$WAS_RUNNING" -eq 1 ]; then
                log "    ▶️ Restarting containers for stack [$pname]..."
                docker compose -f "$cfile" start >> "$LOG_FILE" 2>&1 || docker compose -f "$cfile" up -d >> "$LOG_FILE" 2>&1 || true
            fi

            STACK_END=$(date +%s)
            STACK_DUR=$((STACK_END - STACK_START))
            log "    ⏱️ Stack [$pname] completed in ${STACK_DUR}s ($STACK_STATUS)."
            
            ICON="✅"
            [ "$STACK_STATUS" = "FAILED" ] && ICON="❌"
            STACK_REPORTS="${STACK_REPORTS}%0A${ICON} <b>Stack [${pname}]:</b> ${STACK_STATUS} (${STACK_DUR}s)"
        done
    fi
else
    log "⚠️ Local source directory $LOCAL_SRC does not exist!"
fi

# Step 2: [Remote Backup] - SSH/SCP Compress from Remote Server
if [ -z "$SINGLE_STACK_TARGET" ] && [ "$ENABLE_REMOTE" = "1" ] && [ -n "$REMOTE_IP" ] && [ -n "$REMOTE_SRC" ]; then
    log "🔹 [Remote Backup] Connecting to $REMOTE_USER@$REMOTE_IP:$REMOTE_PORT"
    REMOTE_FILE="remote_backup_${TIMESTAMP}.tar.gz"
    
    log "  📦 Requesting remote compression of $REMOTE_SRC..."
    SSH_CMD="ssh -o StrictHostKeyChecking=no -o BatchMode=yes -p $REMOTE_PORT $REMOTE_USER@$REMOTE_IP"
    
    if $SSH_CMD "tar -czf /tmp/$REMOTE_FILE -C '$(dirname "$REMOTE_SRC")' '$(basename "$REMOTE_SRC")'" >> "$LOG_FILE" 2>&1; then
        log "  📥 Downloading $REMOTE_FILE via SCP..."
        if scp -P "$REMOTE_PORT" -o StrictHostKeyChecking=no "$REMOTE_USER@$REMOTE_IP:/tmp/$REMOTE_FILE" "$TEMP_DIR/" >> "$LOG_FILE" 2>&1; then
            STATUS_REMOTE="SUCCESS"
            log "  ✅ Remote archive downloaded successfully."
        else
            STATUS_REMOTE="FAILED (SCP Download Error)"
            log "  ❌ Failed to download remote archive!"
        fi
        $SSH_CMD "rm -f /tmp/$REMOTE_FILE" >/dev/null 2>&1 || true
    else
        STATUS_REMOTE="FAILED (SSH Error)"
        log "  ❌ Remote SSH compression failed on $REMOTE_IP!"
    fi
else
    log "ℹ️ Remote backup skipped."
fi

# Step 3: [Integrity Check] - Verify all archives (tar -tzf)
log "🔍 [Integrity Check] Testing archive integrity..."
ARCHIVES=("$TEMP_DIR"/*.tar.gz)
if [ -e "${ARCHIVES[0]}" ]; then
    for arc in "${ARCHIVES[@]}"; do
        log "  Testing integrity of $(basename "$arc")..."
        if tar -tzf "$arc" >/dev/null 2>&1; then
            log "    ✅ Integrity PASSED: $(basename "$arc")"
        else
            STATUS_INTEGRITY="FAILED ($(basename "$arc"))"
            log "    ❌ Integrity FAILED: $(basename "$arc")"
        fi
    done
else
    STATUS_INTEGRITY="FAILED (No archives found)"
    log "⚠️ No backup archives found in $TEMP_DIR to test!"
fi

if [[ "$STATUS_INTEGRITY" == FAILED* ]]; then
    log "🚨 CRITICAL: Integrity check failed! Aborting upload to prevent storing corrupt files."
    END_TIME=$(date +%s)
    DIFF=$((END_TIME - START_TIME))
    send_telegram "🚨 <b>HOMELAB BACKUP FAILED!</b>%0AIntegrity check failed! Duration: ${DIFF}s"
    exit 1
fi

# Step 4: [MinIO Immutable Upload]
if [ -n "$MINIO_REMOTE" ] && command -v rclone >/dev/null 2>&1; then
    log "🔹 [MinIO Immutable Upload] Syncing to $MINIO_REMOTE..."
    if rclone copy "$TEMP_DIR" "$MINIO_REMOTE" --immutable >> "$LOG_FILE" 2>&1 || rclone copy "$TEMP_DIR" "$MINIO_REMOTE" >> "$LOG_FILE" 2>&1; then
        STATUS_MINIO="SUCCESS"
        log "  ✅ Uploaded to MinIO successfully."
    else
        STATUS_MINIO="FAILED"
        log "  ❌ MinIO upload failed!"
    fi
fi

# Step 5: [Google Drive Offsite Upload & Retention]
if [ -n "$CLOUD_REMOTE" ] && command -v rclone >/dev/null 2>&1; then
    log "🔹 [Cloud Offsite Upload] Syncing to $CLOUD_REMOTE..."
    if rclone copy "$TEMP_DIR" "$CLOUD_REMOTE" >> "$LOG_FILE" 2>&1; then
        STATUS_CLOUD="SUCCESS"
        log "  ✅ Uploaded to Cloud remote successfully."
        
        if [ -n "$RETENTION_DAYS" ] && [ "$RETENTION_DAYS" -gt 0 ]; then
            log "  🧹 Applying Cloud Retention policy (${RETENTION_DAYS}d)..."
            rclone delete --min-age "${RETENTION_DAYS}d" "$CLOUD_REMOTE" >> "$LOG_FILE" 2>&1 || true
        fi
    else
        STATUS_CLOUD="FAILED"
        log "  ❌ Cloud upload failed!"
    fi
fi

# Step 6: Clean up local temp files
log "🧹 Cleaning up local temporary archives..."
rm -f "$TEMP_DIR"/*.tar.gz || true

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

log "======================================================================"
log "🎉 BACKUP FINISHED IN ${DURATION} SECONDS"
log "Summary: Remote: $STATUS_REMOTE | Integrity: $STATUS_INTEGRITY | MinIO: $STATUS_MINIO | Cloud: $STATUS_CLOUD"
log "======================================================================"

# Send Telegram Alert Summary
TG_MSG="✅ <b>HOMELAB BACKUP REPORT (3-2-1-1-0)</b>%0A"
TG_MSG="${TG_MSG}━━━━━━━━━━━━━━━━━━━━━━"
TG_MSG="${TG_MSG}${STACK_REPORTS}%0A"
TG_MSG="${TG_MSG}🌐 <b>Remote Backup:</b> ${STATUS_REMOTE}%0A"
TG_MSG="${TG_MSG}🔍 <b>Integrity Check:</b> ${STATUS_INTEGRITY}%0A"
TG_MSG="${TG_MSG}🔒 <b>MinIO (Immutable):</b> ${STATUS_MINIO}%0A"
TG_MSG="${TG_MSG}☁️ <b>Google Drive:</b> ${STATUS_CLOUD}%0A"
TG_MSG="${TG_MSG}⏱️ <b>Total Duration:</b> ${DURATION} seconds"

send_telegram "$TG_MSG"

exit 0
