#!/usr/bin/env bash
# Поднимает каталог прицепов на поддомене catalog.jefwipwero.online (nginx + HTTPS).
# Статика, без бэкенда. Запуск на сервере:
#   curl -fsSL https://dxdxxx1212-sys.github.io/trailers-catalog/deploy-subdomain.sh | bash
set -euo pipefail

SUB="catalog.jefwipwero.online"
WWW="/var/www/catalog"
REPO="https://github.com/dxdxxx1212-sys/trailers-catalog.git"

echo "==> [1/5] Пакеты..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx certbot python3-certbot-nginx git

echo "==> [2/5] Загрузка каталога..."
rm -rf "$WWW"
git clone --depth 1 "$REPO" "$WWW"
git config --global --add safe.directory "$WWW" || true
chown -R www-data:www-data "$WWW"

echo "==> [3/5] Конфиг nginx..."
cat > /etc/nginx/sites-available/catalog <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${SUB};
    root ${WWW};
    index index.html;

    location / { try_files \$uri \$uri/ =404; }
    location ~ /\. { deny all; }

    # кэш картинок каталога
    location ~* \.(jpg|jpeg|png|webp|svg)$ {
        expires 30d;
        add_header Cache-Control "public";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/catalog /etc/nginx/sites-enabled/catalog
nginx -t && systemctl reload nginx

echo "==> [4/5] HTTPS (Let's Encrypt)..."
if certbot --nginx -d "${SUB}" --non-interactive --agree-tos -m "admin@jefwipwero.online" --redirect; then
  echo "    HTTPS включён"
else
  echo "    Сертификат пока не выпущен — обычно DNS ещё не указывает на сервер."
  echo "    Сайт уже работает по http://${SUB}. Когда DNS заработает, выполни:"
  echo "    certbot --nginx -d ${SUB} --redirect"
fi

echo "==> [5/5] Автообновление (git pull каждую минуту)..."
( crontab -l 2>/dev/null | grep -v "$WWW"; echo "* * * * * cd $WWW && git pull -q >/dev/null 2>&1" ) | crontab -

echo "==> Готово! Открой: https://${SUB}"
