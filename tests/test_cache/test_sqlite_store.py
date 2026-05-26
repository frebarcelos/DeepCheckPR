import sqlite3
import threading
from pathlib import Path

from pr_analyzer.cache.sqlite_store import SqliteKVStore


def test_sqlite_store_retorna_none_para_chave_ausente(tmp_path: Path) -> None:
    store = SqliteKVStore(tmp_path / "cache.db")
    assert store.get("missing") is None


def test_sqlite_store_set_e_get_roundtrip(tmp_path: Path) -> None:
    store = SqliteKVStore(tmp_path / "cache.db")
    store.set("k1", "biblioteca")
    assert store.get("k1") == "biblioteca"


def test_sqlite_store_persiste_entre_instancias(tmp_path: Path) -> None:
    db = tmp_path / "cache.db"
    SqliteKVStore(db).set("k1", "biblioteca")
    assert SqliteKVStore(db).get("k1") == "biblioteca"


def test_sqlite_store_sobrescreve_valor_existente(tmp_path: Path) -> None:
    store = SqliteKVStore(tmp_path / "cache.db")
    store.set("k1", "old")
    store.set("k1", "new")
    assert store.get("k1") == "new"


def test_sqlite_store_wal_mode_habilitado(tmp_path: Path) -> None:
    db = tmp_path / "cache.db"
    SqliteKVStore(db)
    conn = sqlite3.connect(str(db))
    row = conn.execute("PRAGMA journal_mode").fetchone()
    conn.close()
    assert row[0] == "wal"


def test_sqlite_store_cria_diretorio_pai_se_necessario(tmp_path: Path) -> None:
    db = tmp_path / "sub" / "dir" / "cache.db"
    assert not db.parent.exists()
    SqliteKVStore(db)
    assert db.exists()


def test_sqlite_store_len_retorna_contagem(tmp_path: Path) -> None:
    store = SqliteKVStore(tmp_path / "cache.db")
    assert len(store) == 0
    store.set("k1", "v1")
    store.set("k2", "v2")
    assert len(store) == 2


def test_sqlite_store_tabelas_independentes(tmp_path: Path) -> None:
    db = tmp_path / "cache.db"
    store_a = SqliteKVStore(db, "table_a")
    store_b = SqliteKVStore(db, "table_b")
    store_a.set("key", "value_a")
    assert store_b.get("key") is None


def test_sqlite_store_acesso_concorrente_sem_corrida(tmp_path: Path) -> None:
    store = SqliteKVStore(tmp_path / "cache.db")
    errors: list[Exception] = []

    def write(i: int) -> None:
        try:
            store.set(f"k{i}", f"v{i}")
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=write, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(store) == 20
