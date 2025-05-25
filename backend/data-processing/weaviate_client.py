import os
import json
import weaviate
from weaviate.classes.init import Auth
from weaviate.classes.config import Configure

# ─── Configuration ─────────────────────────────────────────────────────────────
WEAVIATE_API_KEY="RqvU3O6A9IsLJ7eMjhO0ZxYI8uIrewGBsF8o"
WEAVIATE_URL="xz2rb5ctsl6ysou6ewr11q.c0.europe-west3.gcp.weaviate.cloud"
OPENAI_API_KEY="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"

JSON_PATH = "../data/naturalproofs_cleaned.json"   # your flat JSON

# ─── Weaviate Client ────────────────────────────────────────────────────────────
class WeaviateClient:
    def __init__(self, collection_name="proofwiki"):
        self.client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WEAVIATE_URL,
            auth_credentials=Auth.api_key(api_key=WEAVIATE_API_KEY),
            headers={"X-OpenAI-Api-Key": OPENAI_API_KEY}
        )
        assert self.client.is_ready(), "Weaviate cluster is not ready!"
        self.name = collection_name

    def create_dataset(self, overwrite_if_exists: bool = True):
        # delete existing
        if self.client.collections.exists(self.name):
            if overwrite_if_exists:
                self.client.collections.delete(self.name)
            else:
                return
        # create new
        self.client.collections.create(
            name=self.name,
            vectorizer_config=Configure.Vectorizer.text2vec_weaviate()
        )

    def get_collection(self):
        return self.client.collections.get(self.name)

    def add_data(self, entries):
        """
        entries: list of dicts, each with keys:
          id (int), type (str), title (str),
          categories (list of str), contents (str),
          proofs (list of {contents, refs, ref_ids})
        """
        coll = self.get_collection()
        with coll.batch.fixed_size(batch_size=200) as batch:
            for obj in entries:
                batch.add_object({
                    "proof_id":   obj["id"],
                    "type":       obj["type"],
                    "title":      obj["title"],
                    "categories": obj.get("categories", []),
                    "contents":   obj.get("contents", ""),
                    "proofs":     obj.get("proofs", []),
                })
                if batch.number_errors > 10:
                    print("Stopping batch—too many errors.")
                    break

        failed = coll.batch.failed_objects
        if failed:
            print(f"Failed to import {len(failed)} objects; first error: {failed[0]}")

    def query(self, text, top_k=3):
        coll = self.get_collection()
        resp = coll.query.near_text(query=text, limit=top_k)
        return [o.properties for o in resp.objects]

    def close(self):
        self.client.close()


# ─── Main ───────────────────────────────────────────────────────────────────────
def main():
    # 1) Load your flat JSON file
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        entries = json.load(f)

    # 2) Initialize, create collection, and add data
    wv = WeaviateClient(collection_name="proofwiki")
    wv.create_dataset(overwrite_if_exists=True)
    wv.add_data(entries)

    # 4) Close connection
    wv.close()

if __name__ == "__main__":
    main()