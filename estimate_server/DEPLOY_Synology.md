# Estimate(견적) API 서버 — Synology NAS 배포 가이드

견적 프로그램(Estimate v1.3.0 이상)이 쓰는 서버다. **TSERP 서버와 완전히 별개**다 —
컨테이너·포트·이미지·데이터를 하나도 공유하지 않으므로, 이 서버를 배포·재시작해도 TSERP에는
영향이 없다(반대도 마찬가지).

| 항목 | 값 |
|---|---|
| 서버 버전 / API 버전 | 1.1.0 / 1 |
| NAS 폴더 | `/volume1/docker/estimate_server` |
| 포트 | 8100 (TSERP는 8000) |
| 컨테이너 이름 | `estimate-api` |
| DB | SQLite 파일 하나 — `data/estimate.db` (따로 설치할 것 없음) |
| 접속 허용 | 사내망 `192.168.0.0/24`, `192.168.10.0/24` 만. 그 밖(VPN 포함)은 403 |

---

## 1. 최초 배포

### 1-1. 폴더 만들기 (File Station)

```
/volume1/docker/estimate_server/         ← 서버 ZIP을 여기에 푼다
/volume1/docker/estimate_server/data/    ← 직접 만들어 둔다 (estimate.db·backup/이 생기는 곳)
```

`data/` 폴더는 **반드시 미리 만든다**. 없으면 Docker가 root 소유로 만들어 버려 권한 문제가 날 수 있다.

### 1-2. 서버 파일 올리기

`estimate_server_v1.1.0.zip`을 `/volume1/docker/estimate_server/`에 푼다. 결과:

```
estimate_server/
  app.py  store.py  backup.py  config.py  __init__.py
  Dockerfile  docker-compose.yml  requirements.txt  .env.example  .dockerignore
  data/            ← 1-1에서 만든 폴더 (비어 있음)
```

기본값(포트 8100, 사내 대역 두 개)을 그대로 쓸 거면 `.env`는 만들 필요 없다.
바꿀 게 있으면 `.env.example`을 `.env`로 복사해서 고친다.

### 1-3. 컨테이너 띄우기

**방법 A — Container Manager (GUI)**
1. Container Manager → **프로젝트** → **생성**
2. 프로젝트 이름: `estimate_server`
3. 경로: `/volume1/docker/estimate_server`
4. 원본: **기존 docker-compose.yml 사용**
5. 다음 → 완료. 처음에는 이미지 빌드(PyPI에서 패키지 받기) 때문에 1~3분 걸린다.

**방법 B — SSH**
```bash
cd /volume1/docker/estimate_server
sudo /usr/local/bin/docker-compose up -d --build
sudo docker logs -f estimate-api      # Ctrl+C로 빠져나온다
```

### 1-4. 방화벽

DSM → 제어판 → 보안 → 방화벽 → 규칙 편집에서 **TCP 8100** 을 사내 대역
(`192.168.0.0/24`, `192.168.10.0/24`)에만 허용한다. 서버도 접속 IP로 한 번 더 막지만,
바깥에서는 포트 자체가 안 보이게 두는 편이 낫다.

> host 네트워크 모드라 `ports:` 매핑이 없다. 컨테이너가 NAS의 8100번에 바로 붙는다.
> bridge+ports로 바꾸면 접속 IP가 172.x(도커 게이트웨이)로 보여 **모든 요청이 403**이 된다
> (TSERP 3.9.3에서 겪은 것과 같은 이유). 바꾸지 말 것.

---

## 2. 동작 확인

사내 PC의 브라우저에서:

```
http://<NAS IP>:8100/health
```

정상이면:
```json
{"ok":true,"server_version":"1.1.0","api_version":1,"db_ok":true,"error":""}
```

| 보이는 것 | 뜻 |
|---|---|
| 위 JSON, `db_ok: true` | 정상 |
| `"reason":"forbidden"` | 접속한 PC가 허용 대역 밖이다. `.env`의 `ESTIMATE_ALLOWED_CIDRS` 확인 |
| `db_ok: false`, `error`에 내용 | `data/` 폴더 권한 문제일 가능성이 크다. `docker logs estimate-api` 확인 |
| 연결 자체가 안 됨 | 컨테이너가 안 떠 있거나 방화벽. Container Manager에서 상태 확인 |

VPN(Tailscale)으로 접속한 PC에서는 `forbidden`이 나와야 정상이다(사내망 전용).

---

## 3. 견적 프로그램 연결 (각 PC)

1. Estimate v1.3.0 이상 설치
2. **설정 → 데이터 위치 → 견적 서버 지정**에 `<NAS IP>:8100` 입력
3. **연결 확인** → "정상적으로 연결됩니다"
4. **이 서버 사용**
   - 서버에 설정이 없으면(첫 PC) 이 PC의 단가·소재 설정을 서버로 올린다
   - 이미 있으면(두 번째 PC부터) 서버 설정을 가져온다
5. 예전 견적 옮기기(한 번만): **견적 불러오기 → 폴더에서 서버로 올리기…** →
   예전 보관함 폴더(`%LOCALAPPDATA%\MachineEstimate\estimates` 또는 예전 공유 폴더의
   `estimates`) 선택. 서버에 같은 이름이 있으면 덮어쓰지 않고 건너뛴다.

---

## 4. 백업과 복구

### 4-1. 자동 백업

컨테이너가 매일 **23:40**(TSERP 백업 23:30과 겹치지 않게)에 `data/backup/estimate_YYYYMMDD_HHMMSS.db`
스냅샷을 남기고, **30일** 지난 것은 지운다. `.env`로 바꿀 수 있다
(`ESTIMATE_BACKUP_AT`, `ESTIMATE_BACKUP_RETENTION_DAYS`, `ESTIMATE_BACKUP_ENABLED`).

**Hyper Backup 대상에 `/docker/estimate_server/data` 를 추가해 두기를 권한다** (이중 보관).

### 4-1-1. 화면의 [데이터 백업] 단추 (서버 1.2.0+, 프로그램 1.7.0+)

프로그램 도구 모음의 **[데이터 백업]** 을 누르면 그 순간의 스냅샷이 `data/backup/manual_YYYYMMDD_HHMMSS.db`
로 생긴다. 새 폴더를 만들 필요는 없다(`data/backup/`은 서버가 알아서 만든다). 수동 백업은 날짜로 지우지 않고
**최근 50개**만 남긴다. 자동 백업(`estimate_…`)과 같은 폴더·같은 형식이라 4-2의 복구 절차를 그대로 쓴다
(복사할 파일 이름만 `manual_…`로).

### 4-1-2. 편집 암호 (서버 1.2.0+, 프로그램 1.7.0+)

프로그램의 [설정 > 데이터 위치 > 편집 암호]에서 정한다. 암호를 정하면 암호를 입력한 PC에서만 견적 저장·삭제·
신규품목·설정 변경·백업이 되고, 나머지 PC는 읽기 전용(조회·엑셀 출력 가능)이다. 암호는 DB의 `meta` 표에
PBKDF2 해시로만 저장된다. 이 암호가 걸리면 서버가 쓰기 요청을 직접 거절하므로(401), 프로그램을 고쳐 쓰거나 다른
도구로 접속해도 암호 없이는 쓸 수 없다. 암호가 없으면(기본값) 예전처럼 사내망 누구나 쓴다.

### 4-2. 복구 (DB를 특정 날짜로 되돌리기)

```bash
cd /volume1/docker/estimate_server
sudo /usr/local/bin/docker-compose stop
sudo mv data/estimate.db data/estimate.db.broken_$(date +%Y%m%d)
sudo rm -f data/estimate.db-wal data/estimate.db-shm
sudo cp data/backup/estimate_YYYYMMDD_HHMMSS.db data/estimate.db
sudo /usr/local/bin/docker-compose start
```

### 4-3. 지운 견적 되살리기

프로그램에서 삭제한 견적은 실제로 지워지지 않고 표시만 된다.

```bash
cd /volume1/docker/estimate_server
# 지운 목록 보기
sudo docker exec estimate-api python -c "import sqlite3; c=sqlite3.connect('/data/estimate.db'); print(*c.execute('SELECT title, deleted_at, deleted_by FROM estimates WHERE deleted_at IS NOT NULL'), sep='\n')"
# 되살리기 (제목을 정확히)
sudo docker exec estimate-api python -c "import sqlite3; c=sqlite3.connect('/data/estimate.db'); c.execute(\"UPDATE estimates SET deleted_at=NULL, deleted_by='' WHERE title=?\", ('견적 이름',)); c.commit()"
```

### 4-4. 주의

- `data/estimate.db`를 **PC에서 공유 폴더(SMB)로 직접 열지 말 것.** 서버가 쓰는 도중 다른 곳에서
  열면 파일이 깨질 수 있다. 내용을 보려면 `data/backup/`의 스냅샷을 PC로 **복사한 뒤**
  DB Browser for SQLite 등으로 연다.

---

## 5. 서버 업데이트

1. 새 서버 ZIP을 **`data/`와 `.env`를 건드리지 않고** 덮어쓴다(ZIP에는 둘 다 들어 있지 않다).
2. 다시 빌드·재시작:
   - Container Manager: 프로젝트 → `estimate_server` → **빌드** (또는 정지 → 빌드 → 시작)
   - SSH: `sudo /usr/local/bin/docker-compose up -d --build`
3. 2번 동작 확인(`/health`의 `server_version`이 새 버전인지).

API 버전(`api_version`)이 바뀌는 업데이트면 프로그램도 같이 올려야 한다 — 맞지 않는 버전은
프로그램이 "서버 버전이 맞지 않습니다"라고 알리고 서버를 쓰지 않는다.

### 1.0.0 → 1.1.0 (실시간 동기화, 프로그램 v1.4.0과 짝)

- 추가: `GET /changes` — 프로그램이 걸어 두면 누가 저장·삭제하는 순간 응답한다(롱폴링).
  API 버전은 그대로 1이라 v1.3.0 프로그램도 계속 쓸 수 있다(동기화만 안 될 뿐).
- DB는 그대로 쓴다. 처음 뜰 때 `meta` 표에 `library_rev` 한 줄만 더한다(데이터 변환 없음).
- **uvicorn worker는 1개여야 한다.** 변경 알림을 프로세스 안에서 전하므로, `--workers`를
  붙이면 다른 worker의 저장을 듣지 못해 동기화가 늦어진다. 기본 Dockerfile 그대로면 1개다.
- PC 한 대가 연결 하나를 계속 붙잡고 있는다(25초마다 새로 건다). 동시 대기는 16개까지 받고,
  넘치면 기다리지 않고 바로 답한다 — 그 PC들은 몇 초 간격 확인으로 내려앉을 뿐 멈추지 않는다.
- 업데이트 후 확인: `/health`의 `server_version`이 `1.1.0`이고, 브라우저에서
  `http://<NAS>:8100/changes`를 열면 `{"ok":true,"token":"…",…}`가 나온다.

---

## 5. 편집 암호를 잊었을 때

NAS의 `/volume1/docker/estimate_server/.env`에 `ESTIMATE_RESET_EDIT_PASSWORD=1`을 적고 컨테이너를 다시 띄운다.

```bash
cd /volume1/docker/estimate_server
sudo /usr/local/bin/docker-compose up -d --force-recreate
```

시작할 때 편집 암호가 지워지고(모든 PC가 편집 가능) 로그에 `edit password cleared`가 찍힌다. **곧바로 `.env`를
`ESTIMATE_RESET_EDIT_PASSWORD=0`으로 되돌리고 한 번 더 `up -d --force-recreate` 한 뒤**, 프로그램에서 새 암호를 정한다
(안 그러면 컨테이너가 재시작할 때마다 암호가 지워진다).
