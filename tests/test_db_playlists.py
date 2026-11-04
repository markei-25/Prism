import os
import unittest
from unittest.mock import patch

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-anon-key")

import db


class Response:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, supabase, table_name):
        self.supabase = supabase
        self.table_name = table_name
        self.operations = []

    def select(self, fields):
        self.operations.append(("select", fields))
        return self

    def insert(self, values):
        self.operations.append(("insert", values))
        return self

    def update(self, values):
        self.operations.append(("update", values))
        return self

    def delete(self):
        self.operations.append(("delete",))
        return self

    def eq(self, field, value):
        self.operations.append(("eq", field, value))
        return self

    def order(self, field, desc=False):
        self.operations.append(("order", field, desc))
        return self

    def limit(self, value):
        self.operations.append(("limit", value))
        return self

    def execute(self):
        self.supabase.queries.append(self)
        return Response(self.supabase.responses[self.table_name].pop(0))


class FakeSupabase:
    def __init__(self, responses):
        self.responses = responses
        self.queries = []

    def table(self, table_name):
        return FakeQuery(self, table_name)


class PlaylistDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.fake = FakeSupabase({"playlists": [], "playlist_tracks": []})
        self.supabase_patch = patch.object(db, "supabase", self.fake)
        self.supabase_patch.start()

    def tearDown(self):
        self.supabase_patch.stop()

    def test_create_and_fetch_playlists_are_user_scoped(self):
        self.fake.responses["playlists"] = [
            [{"id": "p1", "user_id": "user-1", "name": "Road mix"}],
            [{"id": "p2", "user_id": "user-1", "name": "Focus"}],
        ]

        created = db.create_playlist("user-1", "  Road mix  ")
        fetched = db.fetch_user_playlists("user-1")

        self.assertEqual(created["id"], "p1")
        self.assertEqual(
            self.fake.queries[0].operations[0],
            ("insert", {"user_id": "user-1", "name": "Road mix"}),
        )
        self.assertIn(("eq", "user_id", "user-1"), self.fake.queries[1].operations)
        self.assertEqual(fetched[0]["id"], "p2")

    def test_rename_and_delete_filter_by_playlist_and_account(self):
        self.fake.responses["playlists"] = [
            [{"id": "p1", "user_id": "user-1", "name": "Renamed"}],
            [{"id": "p1"}],
        ]

        db.rename_playlist("user-1", "p1", "Renamed")
        db.delete_playlist("user-1", "p1")

        for query in self.fake.queries:
            self.assertIn(("eq", "id", "p1"), query.operations)
            self.assertIn(("eq", "user_id", "user-1"), query.operations)

    def test_jamendo_track_data_is_saved_without_local_file_paths(self):
        self.fake.responses["playlist_tracks"] = [
            [{"position": 0}],
            [{"id": "entry-1"}],
            [{"track_data": {"jamendo_id": "jam-1", "source": "jamendo"}}],
        ]
        track = {
            "jamendo_id": "jam-1",
            "title": "Cloud track",
            "source": "jamendo",
            "audio_url": "https://example.test/stream",
            "audio_path": "C:\\private\\local.mp3",
        }

        db.add_playlist_track("user-1", "p1", track)
        saved = db.fetch_playlist_tracks("user-1", "p1")

        insert = next(
            operation
            for operation in self.fake.queries[1].operations
            if operation[0] == "insert"
        )
        self.assertNotIn("audio_path", insert[1]["track_data"])
        self.assertEqual(insert[1]["user_id"], "user-1")
        self.assertEqual(saved[0]["jamendo_id"], "jam-1")

    def test_local_track_is_rejected_by_cloud_playlist_storage(self):
        with self.assertRaises(ValueError):
            db.add_playlist_track(
                "user-1",
                "p1",
                {"source": "local", "audio_path": "C:\\private\\local.mp3"},
            )
        self.assertEqual(self.fake.queries, [])


if __name__ == "__main__":
    unittest.main()
