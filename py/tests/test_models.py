"""The models/ folder: recognising a model, finding the one bachmcp.toml names, choosing GGUF files, --use."""

import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bach_mcp.config import Config, ConfigError, model_format  # noqa: E402
from bach_mcp.model.backends import command  # noqa: E402
from bach_mcp.utilities.download import (  # noqa: E402
    CatalogEntry, DownloadJob, ModelInfo, Plan, gguf_files, in_use, list_models, load_catalog, parse, use_in_config)


def touch(path, size=10):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"x" * size)


class ModelsFolderTest(unittest.TestCase):
    def setUp(self):
        self.models = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.models)
        for module in ("bach_mcp.config", "bach_mcp.utilities.download"):
            patcher = mock.patch(f"{module}.MODELS_DIR", self.models)
            patcher.start()
            self.addCleanup(patcher.stop)
        touch(os.path.join(self.models, "Qwen-4bit", "config.json"))
        touch(os.path.join(self.models, "Qwen-4bit", "model.safetensors"), 2000)
        touch(os.path.join(self.models, "Qwen-GGUF", "Qwen-Q4_K_M-00002-of-00002.gguf"))
        touch(os.path.join(self.models, "Qwen-GGUF", "Qwen-Q4_K_M-00001-of-00002.gguf"))
        touch(os.path.join(self.models, "empty", "notes.txt"))
        touch(os.path.join(self.models, "README.md"))


class RecogniseTests(ModelsFolderTest):
    def test_each_format_is_recognised(self):
        self.assertEqual(model_format(os.path.join(self.models, "Qwen-4bit")), "mlx")
        self.assertEqual(model_format(os.path.join(self.models, "Qwen-GGUF")), "gguf")
        self.assertEqual(model_format(os.path.join(self.models, "empty")), "")

    def test_the_list(self):
        models = {m.name: m for m in list_models()}
        self.assertEqual(set(models), {"Qwen-4bit", "Qwen-GGUF", "empty"}, "the README is not a model")
        self.assertEqual((models["Qwen-4bit"].format, models["Qwen-4bit"].size), ("mlx", 2010))


class FindTests(ModelsFolderTest):
    def config(self, model):
        config = Config()
        config.model.model = model
        return config

    def test_a_name_in_models_is_enough(self):
        config = self.config("Qwen-4bit")
        self.assertEqual(config.model_path, os.path.join(self.models, "Qwen-4bit"))
        config.check_model()
        self.assertIn(os.path.join(self.models, "Qwen-4bit"), command(config, 1))
        self.assertTrue(in_use(ModelInfo("Qwen-4bit", "mlx", 0, os.path.join(self.models, "Qwen-4bit")), config))

    def test_a_gguf_folder_gives_its_first_part(self):
        config = self.config("Qwen-GGUF")
        self.assertEqual(config.model_path, os.path.join(self.models, "Qwen-GGUF", "Qwen-Q4_K_M-00001-of-00002.gguf"))
        config.check_model()
        args = command(config, 1)
        self.assertEqual(args[1:3], ["--model", config.model_path])

    def test_a_repo_name_goes_to_the_server_as_it_is(self):
        config = self.config("mlx-community/Other-4bit")
        self.assertEqual(config.model_path, "mlx-community/Other-4bit")
        config.check_model()

    def test_mistakes_say_what_to_do(self):
        with self.assertRaisesRegex(ConfigError, "holds no model"):
            self.config("empty").check_model()
        with self.assertRaisesRegex(ConfigError, "no such file or folder"):
            self.config("models/missing").check_model()


    def test_the_runtime_follows_from_the_model(self):
        self.assertEqual(self.config("Qwen-4bit").backend, "mlx")
        self.assertEqual(self.config("Qwen-GGUF").backend, "gguf")
        self.assertEqual(self.config("mlx-community/Other-4bit").backend, "mlx")
        self.assertEqual(self.config("unsloth/Other-GGUF").backend, "gguf")
        self.assertEqual(self.config("user/other:Q5_K_M").backend, "gguf")
        self.assertEqual(self.config("~/models/x.gguf").backend, "gguf")


class GgufChoiceTests(unittest.TestCase):
    FILES = ["README.md", "Qwen-Q4_K_M.gguf", "Qwen-Q4_K_S.gguf", "Qwen-Q8_0.gguf", "mmproj-F16.gguf"]

    def test_the_named_quantization(self):
        self.assertEqual(gguf_files(self.FILES, "q8_0"), ["Qwen-Q8_0.gguf"])
        self.assertEqual(gguf_files(self.FILES, "Q4_K_S"), ["Qwen-Q4_K_S.gguf"])

    def test_q4_k_m_when_none_is_named_and_the_only_file_alone(self):
        self.assertEqual(gguf_files(self.FILES), ["Qwen-Q4_K_M.gguf"])
        self.assertEqual(gguf_files(["only-IQ2_M.gguf"]), ["only-IQ2_M.gguf"])

    def test_every_part_of_a_split_model(self):
        files = [f"big-Q5_K_M-0000{i}-of-00003.gguf" for i in (2, 1, 3)] + ["big-Q4_K_M.gguf"]
        self.assertEqual(gguf_files(files, "Q5_K_M"), sorted(files[:3]))

    def test_a_missing_quantization_lists_the_others(self):
        with self.assertRaises(ConfigError) as ctx:
            gguf_files(self.FILES, "Q6_K")
        self.assertIn("Q4_K_M", str(ctx.exception))
        self.assertIn("Q8_0", str(ctx.exception))


class UseTests(unittest.TestCase):
    def test_use_sets_the_model_and_keeps_the_comments(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        path = os.path.join(folder, "bachmcp.toml")
        with open(path, "w", encoding="utf-8") as f:
            f.write('[model]\nmodel = ""        # the model\n\n'
                    '[chat]\nmodel = "not this one"\n')
        use_in_config(ModelInfo("Qwen-GGUF", "gguf", 0, ""), path)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn('model = "Qwen-GGUF"        # the model', text)
        self.assertIn('[chat]\nmodel = "not this one"', text)


class NamingTests(unittest.TestCase):
    CATALOG = {"qwen": CatalogEntry("qwen", "unsloth/Qwen-GGUF:Q6_K", "gguf", 9.9, "")}

    def where(self, spec):
        return parse(spec, self.CATALOG)

    def test_a_name_from_the_catalogue(self):
        self.assertEqual(self.where("QWEN"), {"repo": "unsloth/Qwen-GGUF", "quant": "Q6_K", "file": None, "url": None})

    def test_a_repo_with_or_without_a_quantization(self):
        self.assertEqual(self.where("mlx-community/Qwen3-8B-4bit")["repo"], "mlx-community/Qwen3-8B-4bit")
        self.assertEqual(self.where("user/m-GGUF:q8_0")["quant"], "q8_0")

    def test_hugging_face_links(self):
        self.assertEqual(self.where("https://huggingface.co/mlx-community/Qwen3-8B-4bit"),
                         {"repo": "mlx-community/Qwen3-8B-4bit", "quant": None, "file": None, "url": None})
        self.assertEqual(self.where("https://huggingface.co/mlx-community/Qwen3-8B-4bit/tree/main")["file"], None)
        for kind in ("blob", "resolve"):
            where = self.where(f"https://huggingface.co/unsloth/Q-GGUF/{kind}/main/Q-Q4_K_M.gguf")
            self.assertEqual((where["repo"], where["file"]), ("unsloth/Q-GGUF", "Q-Q4_K_M.gguf"))
        self.assertEqual(self.where("https://hf.co/a/b")["repo"], "a/b")

    def test_a_direct_link_must_be_a_gguf_file(self):
        self.assertEqual(self.where("https://example.org/models/q.gguf")["url"], "https://example.org/models/q.gguf")
        with self.assertRaisesRegex(ConfigError, "must point at a .gguf file"):
            self.where("https://example.org/models/")
        with self.assertRaisesRegex(ConfigError, "not a model name"):
            self.where("just-a-word")

    def test_the_catalogue_file(self):
        catalog = load_catalog()
        self.assertIn("qwen3.8-27b", catalog)
        for entry in catalog.values():
            self.assertRegex(entry.repo, r"^[\w.-]+/[\w.-]+(:\w+)?$", entry.name)
            self.assertIn(entry.format, ("mlx", "gguf"), entry.name)
            self.assertEqual(entry.format == "gguf", ":" in entry.repo, f"{entry.name}: a GGUF entry names its quantization")
            self.assertTrue(entry.note, entry.name)
        self.assertEqual(catalog["qwen3.8-27b"].folder, "Qwen3.8-27B-4bit")


FAKE_DOWNLOAD = """
import os, sys, time
target, fail = sys.argv[1], sys.argv[2] == "fail"
os.makedirs(target, exist_ok=True)
for i in range(4):
    with open(os.path.join(target, f"model-{i}.safetensors"), "wb") as f:
        f.write(b"x" * 250)
    time.sleep(0.15)
if fail:
    print("401 Client Error: no access to this repo", flush=True)
    sys.exit(1)
open(os.path.join(target, "config.json"), "w").close()
"""


class DownloadJobTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.events = []

    def job(self, mode="ok", every=0.05):
        plan = Plan("fake", "Fake-4bit", "mlx", 1000, repo="user/Fake-4bit")
        job = DownloadJob(plan, on_progress=lambda d, t: self.events.append(("progress", d, t)),
                          on_done=lambda info: self.events.append(("done", info.format, info.size)),
                          on_error=lambda m: self.events.append(("error", m)), every=every, folder=self.folder,
                          command=[sys.executable, "-c", FAKE_DOWNLOAD, os.path.join(self.folder, "Fake-4bit"), mode],
                          log_path=os.path.join(self.folder, "download.log"))
        job.start()
        return job

    def wait(self, job):
        deadline = time.time() + 10
        while not self.events or self.events[-1][0] == "progress":
            self.assertLess(time.time(), deadline)
            time.sleep(0.02)

    def test_progress_then_done(self):
        self.wait(self.job())
        done = [e[1] for e in self.events if e[0] == "progress"]
        self.assertGreater(len(done), 2)
        self.assertEqual(done, sorted(done), "progress only grows")
        self.assertTrue(all(t == 1000 for _, _, t in [e for e in self.events if e[0] == "progress"]))
        self.assertEqual(self.events[-1], ("done", "mlx", 1000))

    def test_a_failure_says_why(self):
        self.wait(self.job("fail"))
        self.assertEqual(self.events[-1], ("error", "401 Client Error: no access to this repo"))

    def test_stop(self):
        job = self.job(every=0.02)
        time.sleep(0.2)
        job.stop()
        self.wait(job)
        self.assertEqual(self.events[-1], ("error", "stopped"))
        self.assertFalse(job.running)


if __name__ == "__main__":
    unittest.main()
