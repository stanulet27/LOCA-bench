"""Generate task-configs/perturb_pair_16k.json: matched vanilla/perturbed SetConfCrDdl configs
for each of LOCA's 16K seeds.

Usage (from repo root):
    python scripts/make_perturb_pair.py
"""
import copy
import json

SEEDS = [42, 123, 456, 789, 2024]
SOURCE = "task-configs/final_16k_set_config.json"
OUT = "task-configs/perturb_pair_16k.json"

PERTURBATIONS = {
    "base_offset_hours": 3,
    "revisions": [
        {"id": "r1", "step": 3, "delta_hours": 1, "salience": "explicit",
         "message": "Change of plans: set the camera-ready reminders 1 hour earlier than the note says."},
        {"id": "r2", "trigger": "on_finish", "delta_hours": 2, "salience": "offhand",
         "message": "Oh wait, before you wrap up. My mornings are a mess lately, so give me another 2 hours of buffer on all of those reminders."},
        {"id": "r3", "trigger": "on_finish", "delta_hours": 4, "salience": "explicit",
         "message": "Sorry, one more: move every camera-ready reminder a further 4 hours earlier than where they are now."},
        {"id": "r4", "trigger": "on_finish", "delta_hours": 8, "salience": "offhand",
         "message": "Ugh, I just remembered I'm traveling that week. Can you push all the reminders another 8 hours earlier? Thanks."},
    ],
}

base = {c["env_params"]["seed"]: c
        for c in json.load(open(SOURCE))["configurations"] if c["name"] == "SetConfCrDdlS2LEnv"}

configs = []
for seed in SEEDS:
    van = copy.deepcopy(base[seed])
    van["name"] = "SetConfCrDdl16k_vanilla"
    per = copy.deepcopy(base[seed])
    per["name"] = "SetConfCrDdl16k_perturbed"
    per["env_params"]["perturbations"] = PERTURBATIONS
    for cfg in (van, per):
        # python_execute isn't sandboxed: it can read ../groundtruth_workspace (answer key and
        # future revisions) and dump the raw databases. This task doesn't need it.
        cfg["mcp_servers"]["python_execute"]["enabled"] = False
        
    configs += [van, per]

json.dump({"configurations": configs}, open(OUT, "w"), indent=2)
print(f"Wrote {len(configs)} configs ({len(SEEDS)} seeds x vanilla/perturbed) to {OUT}")