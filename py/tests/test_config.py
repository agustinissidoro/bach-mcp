"""bachmcp.toml: what is accepted, what is refused, and when the model settings are checked."""

import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.config import DEFAULT_CONFIG_PATH, REPO_ROOT, Config, ConfigError, load_config  # noqa: E402


class LoadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)

    def load(self, text):
        path = os.path.join(self.folder, "bachmcp.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return load_config(path)

    def test_the_repository_file_loads(self):
        config = load_config(DEFAULT_CONFIG_PATH)
        self.assertIn(config.backend, ("mlx", "gguf"))

    def test_values_and_derived_paths(self):
        config = self.load('[model]\nmodel = "a/b:Q4"\n[server]\nport = 9000\n')
        self.assertEqual((config.backend, config.url, config.mcp_url), ("gguf", "http://127.0.0.1:9000", "http://127.0.0.1:9000/mcp"))

    def test_mistakes_are_refused_with_their_place(self):
        for text, words in [('[modle]\n', "unknown section [modle]"),
                            ('[model]\nbakend = "mlx"\n', '[model] unknown key "bakend"'),
                            ('[generation]\ntemperature = "hot"\n', "[generation] temperature must be a number"),
                            ('[chat]\ndocs = "yes"\n', "[chat] docs must be true or false"),
                            ('[generation]\nreasoning = "high"\n', '[generation] reasoning must be "off" or "on"'),
                            ('[ollama]\nurl = "x"\n', "unknown section [ollama]"),
                            ('[model]\nbackend = "mlx"\n', "Bach reads it from the model. Remove that line"),
                            ('[max]\nbuffer = "b.txt"\n', "[max] buffer is no longer set: each instance has its own file"),
                            ('[algo]\ndir = "x"\n', "[algo] dir is no longer set: algorithms go to the playground")]:
            with self.assertRaises(ConfigError, msg=text) as ctx:
                self.load(text)
            self.assertIn(words, str(ctx.exception))

    def test_an_explicit_file_must_exist(self):
        with self.assertRaises(ConfigError):
            load_config(os.path.join(self.folder, "missing.toml"))


class ModelCheckTests(unittest.TestCase):
    def test_model_settings_are_checked_only_when_a_model_starts(self):
        config = Config()  # model empty: fine for Claude's door
        with self.assertRaises(ConfigError) as ctx:
            config.check_model()
        self.assertIn("no model: [model] model in bachmcp.toml is empty", str(ctx.exception))
        self.assertIn("download", str(ctx.exception), "it says how to get one")

    def test_backend_and_limits(self):
        config = Config()
        config.model.model = "/no/such/model.gguf"
        with self.assertRaisesRegex(ConfigError, "no such file"):
            config.check_model()
        config.model.model = "user/repo:Q4"
        config.generation.max_tokens = config.model.context_size
        with self.assertRaisesRegex(ConfigError, "max_tokens must be smaller"):
            config.check_model()


if __name__ == "__main__":
    unittest.main()
