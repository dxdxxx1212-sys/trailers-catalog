#!/usr/bin/env bash
# Поднимает каталог на бренд-поддомене каталог.восток-прицеп.рф (nginx + HTTPS).
# Переиспользует уже существующий /var/www/catalog (с автодеплоем git pull).
# Запуск на сервере:
#   curl -fsSL https://dxdxxx1212-sys.github.io/trailers-catalog/subdomain-catalog-vostok.sh | bash
set -euo pipefail

SUB="xn--80aajzhsz.xn----ctbklixakchgm2d.xn--p1ai"   # каталог.восток-прицеп.рф (punycode)
WWW="/var/www/catalog"
REPO="https://github.com/dxdxxx1212-sys/trailers-catalog.git"
EMAIL="admin@jefwipwero.online"

echo "==> [1/5] Пакеты..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y nginx certbot python3-certbot-nginx git

echo "==> [2/5] Контент каталога (переиспользуем /var/www/catalog)..."
if [ ! -d "$WWW/.git" ]; then
  rm -rf "$WWW"
  git clone --depth 1 "$REPO" "$WWW"
else
  cd "$WWW" && git pull -q || true
fi
git config --global --add safe.directory "$WWW" || true
chown -R www-data:www-data "$WWW"

echo "==> [3/5] Конфиг nginx для каталог.восток-прицеп.рф..."
cat > /etc/nginx/sites-available/catalog-vostok <<NGINX
server {
    listen 80;
    listen [::]:80;
    server_name ${SUB};
    root ${WWW};
    index index.html;

    location / { try_files \$uri \$uri/ =404; }
    location ~ /\. { deny all; }

    location ~* \.(jpg|jpeg|png|webp|svg)\$ {
        expires 30d;
        add_header Cache-Control "public";
    }
}
NGINX
ln -sf /etc/nginx/sites-available/catalog-vostok /etc/nginx/sites-enabled/catalog-vostok
nginx -t && systemctl reload nginx

echo "==> [4/5] HTTPS (Let's Encrypt)..."
if certbot --nginx -d "${SUB}" --non-interactive --agree-tos -m "${EMAIL}" --redirect; then
  echo "    HTTPS включён"
else
  echo "    !! Сертификат пока не выпущен — скорее всего DNS ещё не указывает на сервер,"
  echo "       либо у домена есть AAAA-запись (IPv6), которую надо удалить (как было с 'подбор')."
  echo "       Сайт уже работает по http://каталог.восток-прицеп.рф"
  echo "       Когда DNS будет ок, выполни:  certbot --nginx -d ${SUB} --redirect"
fi

echo "==> [5/5] Автообновление (git pull каждую минуту)..."
( crontab -l 2>/dev/null | grep -v "cd $WWW && git pull"; echo "* * * * * cd $WWW && git pull -q >/dev/null 2>&1" ) | crontab -

echo "==> Готово! Открой: https://каталог.восток-прицеп.рф"
