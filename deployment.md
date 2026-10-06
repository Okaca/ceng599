# Deployment

How to run the market scraper on a Raspberry Pi, scraping A101, CarrefourSA, Getir, Migros and Şok
every day at **06:00 Istanbul time**.

The scraper image is built on the PC, pushed to Docker Hub as `metu1onurc1/market-scraper`,
and pulled by the Pi. The Pi never needs the source code.

```
PC (project folder)                Docker Hub                          Raspberry Pi (~/marketScraper)
docker buildx build --push   →   metu1onurc1/market-scraper   →   docker compose pull / up
```

## How it runs on the Pi

```
docker compose
├── postgres  (market_postgres)  PostgreSQL 17, data kept in the "pgdata" volume
│                                 tables created from db/init.sql on first start
└── scraper   (market_scraper)   supercronic runs docker/crontab:
                                  06:00 daily → python run_spiders.py → all 5 spiders
                                  → saves to postgres, writes logs/<date>/
```

- The two containers talk over Docker's internal network; the scraper reaches the
  database at host `postgres`, port `5432`.
- `restart: unless-stopped` brings both back after a crash or a reboot.
- A full run takes about 20–30 minutes (Migros alone is ~10).

## 1. Requirements

- Raspberry Pi 4 or 5, **2 GB RAM or more** (4 GB recommended), 16 GB+ SD card or SSD.
  The database grows about 3–4 GB per year.
- **Raspberry Pi OS 64-bit** (Bookworm or newer). The image needs ARM64; the 32-bit OS will not work.
  Check with `uname -m`, which must print `aarch64`.
- Internet access.
- On the PC: Docker Desktop, logged in to Docker Hub as `metu1onurc1`.

## 2. Install Docker on the Pi

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER      # use docker without sudo
sudo systemctl enable docker       # start Docker on boot
```

Log out and back in (or reboot) so the group change takes effect, then check:

```bash
docker version
docker compose version
```

## 3. Build and push the image (PC)

Building for the Pi's ARM64 and for normal PCs (amd64) at once needs a `docker-container`
builder; Docker Desktop's default `desktop-linux` builder can only build one platform.
Check which builders exist (`*` marks the current one):

```powershell
docker buildx ls
```

If there is no `multiarch` builder yet, create it once:

```powershell
docker buildx create --name multiarch --driver docker-container
docker buildx inspect multiarch --bootstrap
```

Then, in the project folder (`C:\Users\okaca\Desktop\ceng599project\marketScraper`):

```powershell
docker buildx build --builder multiarch `
  --platform linux/amd64,linux/arm64 `
  -t metu1onurc1/market-scraper:latest `
  --push .
```

`--builder multiarch` works whichever builder is the default, so this does not depend on
`docker buildx use`. The ARM64 half is built by emulation: expect 7–10 minutes the first time,
less later thanks to the builder's cache. `.dockerignore` keeps `.env`, `venv/` and `logs/` out
of the image, so the image holds no passwords.

Check both platforms were pushed:

```powershell
docker buildx imagetools inspect metu1onurc1/market-scraper:latest
```

It should list `linux/amd64` and `linux/arm64`.

## 4. Set up the folder on the Pi

```bash
mkdir -p ~/marketScraper/db ~/marketScraper/logs
cd ~/marketScraper
```

The Pi needs three files:

```
~/marketScraper/
├── docker-compose.yml   below
├── .env                 database login
├── db/init.sql          creates the tables on the database's first start
└── logs/                scraper logs, one folder per day
```

### `~/marketScraper/docker-compose.yml`

```yaml
services:
  postgres:
    image: postgres:17-alpine
    container_name: market_postgres
    restart: unless-stopped
    env_file: .env
    ports:
      # reachable from other computers on the network (DBeaver, pgAdmin) at <pi-address>:5432.
      # Use "127.0.0.1:5432:5432" to allow only the Pi itself. Never forward this port on the router.
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
    logging:
      # cap Docker's own log of the container; Docker keeps it forever by default
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

  scraper:
    image: metu1onurc1/market-scraper:latest
    container_name: market_scraper
    restart: unless-stopped
    env_file: .env
    environment:
      # inside the compose network the database is reached by its service name
      POSTGRES_HOST: postgres
      POSTGRES_PORT: "5432"
    volumes:
      - ./logs:/app/logs
    depends_on:
      postgres:
        condition: service_healthy
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"

volumes:
  # the database files; survives container updates, deleted only by "docker compose down -v"
  pgdata:
```

### `~/marketScraper/db/init.sql`

The project's `db/init.sql`, unchanged. Paste it, or copy it from the PC
(Windows has `scp` built in; use your Pi's user and address):

```powershell
scp db\init.sql <user>@<pi-address>:~/marketScraper/db/
```

### `~/marketScraper/.env`

```env
POSTGRES_USER=scraper
POSTGRES_PASSWORD=change_me_to_a_long_random_password
POSTGRES_DB=market_db
```

Set a strong password, then make the file readable only by you:

```bash
chmod 600 .env
```

These values are read only when the database is created for the first time; changing them
later needs a reset (see Troubleshooting).

## 5. Start the database

```bash
docker compose up -d postgres
docker compose ps                 # market_postgres ... (healthy)
```

Naming the service starts only the database, so the scraper image is not needed yet.
Check the tables were created (use your `.env` user and database):

```bash
docker compose exec postgres psql -U scraper -d market_db -c "\dt" -c "SELECT * FROM markets;"
```

You should see `markets`, `products` and `prices`, and the 5 markets.

## 6. Move existing data from the PC (optional)

Do this before starting the scraper on the Pi. On the PC (PowerShell), dump the database inside
the container and copy the file out. Do not use `>` redirection here: Windows PowerShell 5.1
re-encodes the output and corrupts the binary dump.

```powershell
docker exec market_postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/market_db.dump'
docker cp market_postgres:/tmp/market_db.dump .\market_db.dump
scp market_db.dump <user>@<pi-address>:~/marketScraper/
```

On the Pi:

```bash
cd ~/marketScraper
docker cp market_db.dump market_postgres:/tmp/market_db.dump
docker compose exec postgres sh -c 'pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists /tmp/market_db.dump'
rm market_db.dump
```

## 7. Start the scraper

```bash
docker compose pull scraper       # downloads the arm64 version automatically
docker compose up -d
docker compose logs scraper       # should show: read crontab: /app/docker/crontab
```

The first run happens at the next 06:00. To fill the database right away:

```bash
docker compose exec scraper python run_spiders.py              # all spiders
docker compose exec scraper python run_spiders.py a101Spider   # only one
```

Once the Pi runs, stop the scraper on the PC so the two machines do not both scrape
(on the PC, in the project folder): `docker compose stop scraper`.

## 8. Check a run

Each run writes to `~/marketScraper/logs/<date>/`:

- `summary.txt`: one line per spider plus today's saved prices per market, e.g.

  ```
  a101Spider          8433 items     0 dropped    0.9 min   ok
  getirSpider         9222 items     0 dropped    1.3 min   ok

  a101                8431 prices today, 8429 on the previous run
  ```

  A spider is marked `FAILED` when it crashed, saved nothing or logged errors, and a market gets a
  `WARNING` when it saved under 80% of its previous run's prices.
- `<spider>.log`: the full Scrapy log of each spider.

Logs older than 30 days are deleted automatically (prices are never deleted). The scheduler's own
output is in `docker compose logs scraper`.

Count today's prices directly in the database:

```bash
docker compose exec postgres psql -U scraper -d market_db -c "
  SELECT m.name, count(*) FROM prices pr
  JOIN products p ON p.id = pr.product_id JOIN markets m ON m.id = p.market_id
  WHERE (pr.scraped_at AT TIME ZONE 'Europe/Istanbul')::date = (now() AT TIME ZONE 'Europe/Istanbul')::date
  GROUP BY 1;"
```

## 9. Change the schedule

The time is in `docker/crontab` in the project (standard cron format, Istanbul time):

```
0 6 * * * python /app/run_spiders.py
```

For example `30 6 * * *` is 06:30 every day. The file is part of the image, so after editing it
build and push again and update the Pi (step 10).

## 10. Update the code

After changing spiders, the schedule or anything else in the image:

1. On the PC, build and push as in step 3.
2. On the Pi:

   ```bash
   cd ~/marketScraper
   docker compose pull scraper
   docker compose up -d scraper
   docker image prune -f             # remove the replaced image
   ```

The database keeps its data. A run that is in progress is stopped by the update, so update
outside the 06:00–06:30 window. If `db/init.sql` changed, see "Database changes" in Troubleshooting.

## 11. Backups

The data lives in the `pgdata` Docker volume. A dump per week with cron on the Pi
(`crontab -e`), keeping the last 8:

```
0 3 * * 0 cd ~/marketScraper && docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > backups/market_db_$(date +\%F).dump && ls -t backups/*.dump | tail -n +9 | xargs -r rm
```

Create the folder first with `mkdir -p ~/marketScraper/backups`. SD cards wear out, so copy
backups off the Pi now and then. The same dump moves the data to a VPS later: restore it there
as in step 6.

## 12. Security

- The image holds no passwords; the login lives only in the Pi's `.env`.
- New Docker Hub repositories are public by default, so anyone can pull the image (the code, not
  the data). To make it private, change it on hub.docker.com under the repository's settings, then
  run `docker login` on the Pi once so it can still pull.
- The compose file publishes PostgreSQL on port 5432 so you can query it from another computer on
  the network. If you do not need that, change it to `"127.0.0.1:5432:5432"` or remove the
  `ports:` lines. Never forward port 5432 on your router to the internet.

## Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Multi-platform build is not supported for the docker driver` | The build used Docker Desktop's default builder. Add `--builder multiarch` (step 3). |
| `exec format error` on the Pi | 32-bit OS (`uname -m` must print `aarch64`), or the pushed image has no arm64 version: check with `docker buildx imagetools inspect` (step 3). |
| `pull access denied` on the Pi | The repository is private: `docker login` on the Pi. |
| Every spider `FAILED` with connection errors | Database not running: `docker compose ps`, then `docker compose up -d`. |
| Getir `FAILED` or a `WARNING` for getir | Getir briefly rate-limits (403/504). The spider retries 5 times; a one-off miss fills in the next day. If it repeats, check `logs/<date>/getirSpider.log`. |
| A spider suddenly saves 0 items every day | The site changed. The spider needs updating; its log shows where it stopped. |
| Database changes (new `db/init.sql`) are not applied | `init.sql` only runs on an empty database. Back up (step 11), then `docker compose down -v` (**deletes all data**) and `docker compose up -d`, then restore what you need. |
| Changed `.env` password has no effect | Same reason as above: the login is set when the database is first created. |
| Times look 3 hours off | Times are stored in UTC (`timestamptz`). Show them in Istanbul time with `scraped_at AT TIME ZONE 'Europe/Istanbul'`. |

## Running on the PC (development)

The project's own `docker-compose.yml` builds the scraper from source instead of pulling it.
To run the spiders with the virtual environment and only the database in Docker:

```powershell
docker compose up -d postgres
venv\Scripts\python run_spiders.py
```
