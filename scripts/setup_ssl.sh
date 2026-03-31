#!/bin/bash
#
# Let's Encrypt SSL Certificate Setup Script for AgonArena Bot
# Domain: 37-46-18-40.sslip.io
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="37-46-18-40.sslip.io"
EMAIL="admin@${DOMAIN}"  # Change this to your actual email
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
WORKSPACE_DIR="/home/openclaw/.openclaw/workspace/agonarena_bot"
SSL_DIR="${WORKSPACE_DIR}/ops/ssl"
NGINX_CONF="${WORKSPACE_DIR}/ops/nginx/agonarena_bot.conf"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if running as root (needed for certbot)
    if [ "$EUID" -ne 0 ]; then 
        log_error "Please run as root (use sudo)"
        exit 1
    fi
    
    # Check if certbot is installed
    if ! command -v certbot &> /dev/null; then
        log_info "Installing certbot..."
        apt-get update
        apt-get install -y certbot
    fi
    
    # Check if nginx is installed
    if ! command -v nginx &> /dev/null; then
        log_error "Nginx is not installed. Please install nginx first."
        exit 1
    fi
    
    log_info "Prerequisites check passed"
}

# Backup existing certificates
backup_existing() {
    if [ -f "${SSL_DIR}/agonarena.crt" ] || [ -f "${SSL_DIR}/agonarena.key" ]; then
        log_info "Backing up existing certificates..."
        BACKUP_DIR="${SSL_DIR}/backup-$(date +%Y%m%d-%H%M%S)"
        mkdir -p "${BACKUP_DIR}"
        cp "${SSL_DIR}/agonarena.crt" "${BACKUP_DIR}/" 2>/dev/null || true
        cp "${SSL_DIR}/agonarena.key" "${BACKUP_DIR}/" 2>/dev/null || true
        log_info "Backup saved to: ${BACKUP_DIR}"
    fi
}

# Obtain certificate from Let's Encrypt
obtain_certificate() {
    log_info "Obtaining Let's Encrypt certificate for ${DOMAIN}..."
    
    # Use standalone mode temporarily (nginx will be stopped briefly)
    certbot certonly --standalone \
        -d "${DOMAIN}" \
        --agree-tos \
        --non-interactive \
        --email "${EMAIL}" \
        --preferred-challenges http
    
    if [ $? -eq 0 ]; then
        log_info "Certificate obtained successfully"
    else
        log_error "Failed to obtain certificate"
        exit 1
    fi
}

# Update nginx configuration with Let's Encrypt paths
update_nginx_config() {
    log_info "Updating nginx configuration..."
    
    # Create new nginx config with Let's Encrypt paths
    cat > "${NGINX_CONF}" << EOF
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} 37.46.18.40.sslip.io vm939255.vds.as210546.net;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${DOMAIN} 37.46.18.40.sslip.io vm939255.vds.as210546.net;

    # Let's Encrypt certificates
    ssl_certificate ${CERT_DIR}/fullchain.pem;
    ssl_certificate_key ${CERT_DIR}/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 300s;
    }
}
EOF
    
    log_info "Nginx configuration updated"
}

# Create symlinks for application compatibility
create_symlinks() {
    log_info "Creating symlinks for application compatibility..."
    
    # Remove old self-signed certs if they exist
    rm -f "${SSL_DIR}/agonarena.crt"
    rm -f "${SSL_DIR}/agonarena.key"
    
    # Create symlinks
    ln -s "${CERT_DIR}/fullchain.pem" "${SSL_DIR}/agonarena.crt"
    ln -s "${CERT_DIR}/privkey.pem" "${SSL_DIR}/agonarena.key"
    
    log_info "Symlinks created"
}

# Setup auto-renewal cron job
setup_auto_renewal() {
    log_info "Setting up auto-renewal cron job..."
    
    # Create renewal script
    RENEW_SCRIPT="${WORKSPACE_DIR}/scripts/renew_ssl.sh"
    cat > "${RENEW_SCRIPT}" << 'EOF'
#!/bin/bash
# Auto-renewal script for Let's Encrypt certificates

CERT_DIR="/etc/letsencrypt/live/37-46-18-40.sslip.io"
WORKSPACE_DIR="/home/openclaw/.openclaw/workspace/agonarena_bot"
SSL_DIR="${WORKSPACE_DIR}/ops/ssl"

# Renew certificates
certbot renew --quiet --deploy-hook "nginx -s reload"

# Ensure symlinks are intact
if [ -f "${CERT_DIR}/fullchain.pem" ]; then
    rm -f "${SSL_DIR}/agonarena.crt"
    rm -f "${SSL_DIR}/agonarena.key"
    ln -s "${CERT_DIR}/fullchain.pem" "${SSL_DIR}/agonarena.crt"
    ln -s "${CERT_DIR}/privkey.pem" "${SSL_DIR}/agonarena.key"
fi
EOF
    
    chmod +x "${RENEW_SCRIPT}"
    
    # Add cron job (run twice daily as recommended by Let's Encrypt)
    CRON_JOB="0 3,15 * * * ${RENEW_SCRIPT} >> /var/log/agonarena-ssl-renewal.log 2>&1"
    
    # Remove existing cron job if present
    crontab -l 2>/dev/null | grep -v "renew_ssl.sh" | crontab - 2>/dev/null || true
    
    # Add new cron job
    (crontab -l 2>/dev/null; echo "${CRON_JOB}") | crontab -
    
    log_info "Auto-renewal cron job installed (runs at 03:00 and 15:00 daily)"
}

# Reload nginx
reload_nginx() {
    log_info "Testing and reloading nginx..."
    
    if nginx -t; then
        systemctl reload nginx
        log_info "Nginx reloaded successfully"
    else
        log_error "Nginx configuration test failed"
        exit 1
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  SSL Setup Completed Successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Domain: ${DOMAIN}"
    echo "Certificate: ${CERT_DIR}"
    echo "Auto-renewal: Enabled (cron job installed)"
    echo ""
    echo "To test renewal (dry-run):"
    echo "  certbot renew --dry-run"
    echo ""
    echo "To manually renew:"
    echo "  ${WORKSPACE_DIR}/scripts/renew_ssl.sh"
    echo ""
}

# Main execution
main() {
    echo "========================================"
    echo "  Let's Encrypt SSL Setup"
    echo "  Domain: ${DOMAIN}"
    echo "========================================"
    echo ""
    
    check_prerequisites
    backup_existing
    obtain_certificate
    update_nginx_config
    create_symlinks
    setup_auto_renewal
    reload_nginx
    print_success
}

# Run main function
main "$@"
