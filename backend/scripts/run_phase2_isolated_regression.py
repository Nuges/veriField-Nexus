#!/usr/bin/env python3
"""Run Phase 2 regression against an explicitly verified disposable Mac container.

No Alembic migrations, app server, production endpoints or existing local DBs.
Run using backend/venv/bin/python; --self-check tests isolation without Docker.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time


GUARD = r'''
import os
import socket
from urllib.parse import urlsplit
import psycopg2
from psycopg2.extensions import make_dsn, parse_dsn

PORT = int(os.environ["VF_PHASE2_ALLOWED_PORT"])
DATABASE = "verifield_phase2_test"
USER = "phase2_test"
LOOPBACK = {"127.0.0.1", "localhost", "::1"}

def reject():
    raise PermissionError("Phase 2 isolation blocked a non-test connection")

def validate_pg(params):
    if params.get("service") or (params.get("hostaddr") and params["hostaddr"] not in LOOPBACK):
        reject()
    host = params.get("host", os.environ.get("PGHOST", ""))
    port = params.get("port", os.environ.get("PGPORT", ""))
    database = params.get("dbname", params.get("database", os.environ.get("PGDATABASE", "")))
    user = params.get("user", os.environ.get("PGUSER", ""))
    if host not in LOOPBACK or str(port) != str(PORT) or database != DATABASE or user != USER:
        reject()

_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex
_getaddrinfo = socket.getaddrinfo
_gethostbyname = socket.gethostbyname
_gethostbyname_ex = socket.gethostbyname_ex
_sendto = socket.socket.sendto

def check_address(address):
    if not isinstance(address, tuple) or address[0] not in LOOPBACK or int(address[1]) != PORT:
        reject()

def connect(sock, address):
    check_address(address)
    return _connect(sock, address)

def connect_ex(sock, address):
    check_address(address)
    return _connect_ex(sock, address)

def getaddrinfo(host, port, *args, **kwargs):
    if host not in LOOPBACK:
        reject()
    return _getaddrinfo(host, port, *args, **kwargs)

def gethostbyname(host):
    if host not in LOOPBACK:
        reject()
    return _gethostbyname(host)

def gethostbyname_ex(host):
    if host not in LOOPBACK:
        reject()
    return _gethostbyname_ex(host)

def sendto(sock, data, *args):
    reject()

socket.socket.connect = connect
socket.socket.connect_ex = connect_ex
socket.getaddrinfo = getaddrinfo
socket.gethostbyname = gethostbyname
socket.gethostbyname_ex = gethostbyname_ex
socket.socket.sendto = sendto

_pg_connect = psycopg2.connect
def pg_connect(dsn=None, *args, **kwargs):
    connection_params = {k: v for k, v in kwargs.items() if k not in {"connection_factory", "cursor_factory", "async", "async_"}}
    validate_pg(parse_dsn(make_dsn(dsn or "", **connection_params)))
    return _pg_connect(dsn, *args, **kwargs)
psycopg2.connect = pg_connect

# asyncpg uses Python sockets; also validate database/user before its TCP connection.
import asyncpg
_async_connect = asyncpg.connect
async def async_connect(dsn=None, *args, **kwargs):
    params = {}
    if dsn:
        url = urlsplit(dsn)
        params = {"host": url.hostname, "port": url.port, "database": url.path.lstrip("/"), "user": url.username}
    params.update({k: v for k, v in kwargs.items() if k in {"host", "port", "database", "user"}})
    validate_pg(params)
    return await _async_connect(dsn, *args, **kwargs)
asyncpg.connect = async_connect
'''


BOOTSTRAP = r'''
import phase2_isolation_guard
import asyncio
import importlib
import os
import uuid
from pathlib import Path
from sqlalchemy import Index, create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base
from app import domains
from app.domains.methodologies.models.base_registry import MethodologyFamily

# Register existing models before DDL, including lazily imported VM0044 tables.
# The ledger's fallback query uses these tables after a calculation was minted.
for source_root in domains.__path__:
    for source in sorted(Path(source_root).rglob("*.py")):
        relative = source.relative_to(source_root)
        if source.name == "models.py" or source.stem.endswith("_models") or "models" in relative.parts[:-1]:
            parts = list(relative.with_suffix("").parts)
            if parts[-1] == "__init__":
                parts.pop()
            importlib.import_module(domains.__name__ + "." + ".".join(parts))

# This process runs before pytest's SQLite fixture edits shared column defaults.
# alembic/env.py supplies this index before any REFERENCES activities(id) DDL.
# ORM create_all alone omits it because Activity has a composite primary key.
# Reproduce that existing schema requirement only in this disposable bootstrap
# process. No model source, migration or operational database is changed.
activities = Base.metadata.tables["activities"]
if not any(index.name == "uq_activities_id" for index in activities.indexes):
    Index("uq_activities_id", activities.c.id, unique=True)
url = make_url(os.environ["POSTGRES_TEST_URL"])
engine = create_engine(url.set(drivername="postgresql+psycopg2"))
with engine.begin() as connection:
    assert connection.execute(text("SELECT current_database()")).scalar() == "verifield_phase2_test"
    assert connection.execute(text("SELECT current_user")).scalar() == "phase2_test"
    print("Disposable PostGIS:", connection.execute(text("SELECT postgis_version()")).scalar(), flush=True)
    existing = inspect(connection).get_table_names(schema="public")
    if ("projects" in existing or "users" in existing) and os.environ.get("VF_PHASE2_RESUME_TEST_CONTAINER") != "1":
        raise RuntimeError("Test container already contains application tables. Use a new disposable container.")
    Base.metadata.create_all(connection)
    print("Existing model tables registered:", len(Base.metadata.tables), flush=True)
engine.dispose()

async def seed_test_catalog():
    engine = create_async_engine(url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        # Existing rehearsal/tenant fixtures refer to these canonical family IDs.
        # They are disposable catalogue fixtures, not operational methodology assignments.
        families = {
            "AGRICULTURE_LAND_USE": "9a7a4370-71e6-44f5-9870-975823b8ccb9",
            "BIOCHAR": "d77b6543-f0f1-4784-a840-cd77e0876a91",
            "COOKSTOVES": "ab748cb8-3b7c-4e07-aec7-d1dc5f3dcf3a",
            "HYBRID_ENERGY": "15fa60cc-d06a-4ef1-ae14-0359e1bd3674",
            "EV_MOBILITY": "ab17ade7-8938-44b1-a24d-bc797a65e056",
        }
        for code, value in families.items():
            if await session.get(MethodologyFamily, uuid.UUID(value)) is None:
                session.add(MethodologyFamily(id=uuid.UUID(value), code=code, name="Isolated test " + code, is_active=True))
        await session.commit()
    await engine.dispose()
asyncio.run(seed_test_catalog())
print("Disposable ORM test schema/family fixtures ready; no migrations executed.", flush=True)
'''


def container_command(socket_path, *args):
    return ["docker", "--host", socket_path, *args]


def verify_container(info, expected_id, port):
    if not re.fullmatch(r"[0-9a-f]{64}", expected_id) or info.get("Id") != expected_id:
        raise RuntimeError("Container ID is not the exact disposable test container.")
    config = info.get("Config", {})
    environment = dict(item.split("=", 1) for item in config.get("Env", []) if "=" in item)
    expected = {"POSTGRES_DB": "verifield_phase2_test", "POSTGRES_USER": "phase2_test", "POSTGRES_PASSWORD": "phase2_test_only"}
    if any(environment.get(key) != value for key, value in expected.items()):
        raise RuntimeError("Unexpected container database configuration.")
    if config.get("Labels", {}).get("verifield.purpose") != "phase2-disposable-test":
        raise RuntimeError("Container lacks the disposable-test label.")
    if config.get("Image") != "postgis/postgis:15-3.4-alpine" or not info.get("State", {}).get("Running"):
        raise RuntimeError("Expected running test PostGIS image.")
    ports = info.get("NetworkSettings", {}).get("Ports", {}).get("5432/tcp", [])
    if ports != [{"HostIp": "127.0.0.1", "HostPort": str(port)}]:
        raise RuntimeError("Database must be bound only to the supplied loopback port.")
    host_config = info.get("HostConfig", {})
    if host_config.get("Binds"):
        raise RuntimeError("Host data binds are forbidden for this test container.")
    # --tmpfs is represented by HostConfig.Tmpfs. --mount type=tmpfs may
    # instead be represented in Mounts. An empty Mounts list is not proof
    # that a --tmpfs mount is missing. Confirm the actual filesystem below.
    data_path = "/var/lib/postgresql/data"
    mounts = info.get("Mounts") or []
    tmpfs_config = host_config.get("Tmpfs") or {}
    declared_tmpfs = isinstance(tmpfs_config, dict) and data_path in tmpfs_config
    if not isinstance(mounts, list):
        raise RuntimeError("Unexpected Docker Mounts format; share storage inspection output.")
    data_mounts = [item for item in mounts if item.get("Destination") == data_path]
    if len(data_mounts) > 1 or any(item.get("Type") != "tmpfs" for item in data_mounts):
        raise RuntimeError("Persistent or conflicting database data mounts are forbidden.")
    if not declared_tmpfs and not data_mounts:
        raise RuntimeError("Database data must use disposable tmpfs storage.")


def verify_tmpfs_mountinfo(mountinfo):
    filesystems = []
    for line in mountinfo.splitlines():
        if " - " not in line:
            continue
        before, after = line.split(" - ", 1)
        fields = before.split()
        if len(fields) >= 5 and fields[4] == "/var/lib/postgresql/data":
            filesystems.append(after.split()[0])
    if filesystems != ["tmpfs"]:
        raise RuntimeError("Actual database filesystem is not a unique tmpfs mount; no database changes made.")


def test_environment(backend, directory, port, sync_postgis=False):
    env = os.environ.copy()
    pg = f"postgresql+asyncpg://phase2_test:phase2_test_only@127.0.0.1:{port}/verifield_phase2_test"
    env.update({
        "DATABASE_URL": f"sqlite+aiosqlite:///{directory / 'regression.sqlite'}",
        "POSTGRES_TEST_URL": pg,
        "POSTGIS_TEST_URL": pg.replace("+asyncpg", "+psycopg2") if sync_postgis else pg,
        "TESTING": "1", "JWT_SECRET": "phase2-isolated-test-secret-not-for-production",
        "REDIS_URL": "redis://127.0.0.1:9/0", "API_BASE_URL": "http://127.0.0.1:9/api/v1",
        "BACKEND_URL": "http://127.0.0.1:9/api/v1", "VF_PHASE2_ALLOWED_PORT": str(port),
        "PGHOST": "127.0.0.1", "PGPORT": str(port), "PGDATABASE": "verifield_phase2_test",
        "PGUSER": "phase2_test", "PGPASSWORD": "phase2_test_only", "PGOPTIONS": "",
        "PYTHONPATH": os.pathsep.join([str(directory), str(backend), str(backend.parent)]),
        "PYTHONUNBUFFERED": "1",
    })
    for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR"):
        env.pop(key, None)
    return env


def run_logged(command, backend, env, log):
    with log.open("w") as output:
        process = subprocess.Popen(command, cwd=backend, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        try:
            for line in process.stdout:
                print(line, end="", flush=True)
                output.write(line)
            return process.wait()
        except KeyboardInterrupt:
            process.terminate()
            process.wait()
            raise


def self_check():
    valid = {
        "Id": "0" * 64,
        "Config": {"Image": "postgis/postgis:15-3.4-alpine", "Labels": {"verifield.purpose": "phase2-disposable-test"},
                   "Env": ["POSTGRES_DB=verifield_phase2_test", "POSTGRES_USER=phase2_test", "POSTGRES_PASSWORD=phase2_test_only"]},
        "State": {"Running": True},
        "NetworkSettings": {"Ports": {"5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": "51916"}]}},
        "HostConfig": {"Tmpfs": {"/var/lib/postgresql/data": ""}}, "Mounts": [],
    }
    verify_container(valid, "0" * 64, 51916)
    modern = json.loads(json.dumps(valid))
    modern["HostConfig"] = {}
    modern["Mounts"] = [{"Destination": "/var/lib/postgresql/data", "Type": "tmpfs"}]
    verify_container(modern, "0" * 64, 51916)
    for mutate in (
        lambda item: item["HostConfig"].clear(),
        lambda item: item["Config"]["Labels"].clear(),
        lambda item: item["HostConfig"].update(Binds=["/existing:/var/lib/postgresql/data"]),
        lambda item: item.update(Mounts=[{"Destination": "/var/lib/postgresql/data", "Type": "volume"}]),
        lambda item: item["NetworkSettings"]["Ports"]["5432/tcp"][0].update(HostIp="0.0.0.0"),
    ):
        invalid = json.loads(json.dumps(valid))
        mutate(invalid)
        try:
            verify_container(invalid, "0" * 64, 51916)
        except RuntimeError:
            continue
        raise AssertionError("Unsafe container metadata accepted")
    verify_tmpfs_mountinfo("77 42 0:33 / /var/lib/postgresql/data rw - tmpfs tmpfs rw")
    for mountinfo in ("", "77 42 0:33 / /var/lib/postgresql/data rw - ext4 /dev/sda rw"):
        try:
            verify_tmpfs_mountinfo(mountinfo)
        except RuntimeError:
            continue
        raise AssertionError("Persistent/missing filesystem accepted")
    print("Storage checks passed: both tmpfs formats accepted; persistent storage rejected.", flush=True)
    # Execute in a fresh subprocess so these monkeypatches never affect the runner.
    directory = Path(tempfile.mkdtemp(prefix="verifield-isolation-selfcheck-"))
    (directory / "phase2_isolation_guard.py").write_text(GUARD)
    code = r'''
import asyncio
import socket
import phase2_isolation_guard as guard
import psycopg2
import asyncpg

guard.validate_pg({"host": "127.0.0.1", "port": 51916, "database": "verifield_phase2_test", "user": "phase2_test"})
for action in [
    lambda: socket.getaddrinfo("example.com", 443),
    lambda: socket.socket().connect(("127.0.0.1", 5432)),
    lambda: socket.socket().connect(("127.0.0.1", 8000)),
    lambda: psycopg2.connect("host=127.0.0.1 port=5432 dbname=postgres user=phase2_test"),
    lambda: psycopg2.connect(host="127.0.0.1", port=51916, dbname="postgres", user="phase2_test"),
    lambda: psycopg2.connect(host="127.0.0.1", hostaddr="203.0.113.1", port=51916, dbname="verifield_phase2_test", user="phase2_test"),
    lambda: psycopg2.connect(service="some_existing_service"),
    lambda: asyncio.run(asyncpg.connect("postgresql://phase2_test@localhost:5432/postgres")),
]:
    try:
        action()
    except PermissionError:
        continue
    raise AssertionError("Isolation failed to reject a non-test connection")
print("Isolation checks passed: external DNS, normal DB/API ports and wrong DB names blocked.")
'''
    env = os.environ.copy()
    env.update({"VF_PHASE2_ALLOWED_PORT": "51916", "PYTHONPATH": str(directory)})
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
    shutil.rmtree(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", type=Path)
    parser.add_argument("--container")
    parser.add_argument("--port", type=int)
    parser.add_argument("--docker-socket", default="unix:///Users/segun/.docker/run/docker.sock")
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--resume-test-container", action="store_true", help="Reuse only the explicitly verified disposable fixture container; creates missing tables without altering existing tables.")
    args = parser.parse_args()
    if args.self_check:
        self_check()
        return 0
    backend = (args.backend_root or Path.cwd()).resolve()
    if not (backend / "app/main.py").is_file() or not (backend / "tests/conftest.py").is_file():
        parser.error("Supply the actual backend directory with --backend-root.")
    if not args.container or not args.port or not 1024 < args.port < 65536 or args.port == 5432:
        parser.error("Supply the exact disposable container ID and its separate local port.")
    if not args.docker_socket.startswith("unix:///"):
        parser.error("Only a local Unix Docker socket is allowed.")
    self_check()
    result = subprocess.run(container_command(args.docker_socket, "inspect", args.container), capture_output=True, text=True, check=True)
    info = json.loads(result.stdout)[0]
    verify_container(info, args.container, args.port)
    mountinfo = subprocess.run(container_command(args.docker_socket, "exec", args.container, "cat", "/proc/self/mountinfo"), capture_output=True, text=True, check=True)
    verify_tmpfs_mountinfo(mountinfo.stdout)
    print("Verified disposable container and actual tmpfs filesystem.", flush=True)
    for attempt in range(45):
        ready = subprocess.run(container_command(args.docker_socket, "exec", args.container, "pg_isready", "-U", "phase2_test", "-d", "verifield_phase2_test"), capture_output=True)
        if ready.returncode == 0:
            break
        time.sleep(1)
    else:
        raise RuntimeError("Disposable database did not become ready; inspect its container logs.")
    directory = Path(tempfile.mkdtemp(prefix="verifield-phase2-full-"))
    (directory / "phase2_isolation_guard.py").write_text(GUARD)
    # Children (including rehearsal subprocesses) inherit the same pre-import guard.
    (directory / "sitecustomize.py").write_text("import os\ntry:\n    import phase2_isolation_guard\nexcept BaseException:\n    os._exit(78)\n")
    (directory / "bootstrap.py").write_text(BOOTSTRAP)
    print("Logs and disposable SQLite database:", directory, flush=True)
    env = test_environment(backend, directory, args.port)
    env["VF_PHASE2_RESUME_TEST_CONTAINER"] = "1" if args.resume_test_container else "0"
    bootstrap_exit = run_logged([sys.executable, str(directory / "bootstrap.py")], backend, env, directory / "bootstrap.log")
    if bootstrap_exit:
        print("Test fixture setup failed; regression was not started. Share bootstrap.log.", flush=True)
        return bootstrap_exit
    # Explicit -p also checks the guard imports normally; sitecustomize covers collection.
    full_exit = run_logged([sys.executable, "-m", "pytest", "-p", "phase2_isolation_guard", "tests/", "-m", "not external_live", "--tb=short", "-q"], backend, env, directory / "backend-full.log")
    # Legacy spatial helpers use sync SQLAlchemy, whereas other modules require asyncpg.
    # Run the authoritative ten-test SQL suite separately with the correct sync driver.
    spatial_env = test_environment(backend, directory, args.port, sync_postgis=True)
    spatial_exit = run_logged([sys.executable, "-m", "pytest", "-p", "phase2_isolation_guard", "tests/domains/earth_observation/test_postgis_authoritative_integration.py", "--tb=short", "-q"], backend, spatial_env, directory / "postgis.log")
    summary = {"bootstrap_exit": bootstrap_exit, "full_backend_exit": full_exit, "postgis_exit": spatial_exit, "logs": str(directory), "container": args.container, "port": args.port, "migrations_executed": False}
    (directory / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("\nPHASE 2 BACKEND CHECK SUMMARY\n" + json.dumps(summary, indent=2), flush=True)
    print("No container was stopped or removed. Keep logs for review.", flush=True)
    return full_exit or spatial_exit


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, subprocess.CalledProcessError) as error:
        print("STOPPED:", error, file=sys.stderr)
        raise SystemExit(1)
