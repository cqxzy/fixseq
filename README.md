A small helper script to create **ProteinMPNN** `fixed_positions_jsonl` from the `parsed.jsonl` produced by `parse_multiple_chains.py`.

It lets you specify **per-chain residue position ranges** in a compact string like:

- `A:1-10,20-30;B:5-8`
- `A:1-10 20-30 | B:5-8`
- `A:*` (special: whole chain)

and outputs the JSONL format that ProteinMPNN expects for **fixed positions**.

---

## What it does

Given:

- `parsed.jsonl` (from ProteinMPNN helper `parse_multiple_chains.py`)
- a list of **designed chains** (e.g., `A` or `A B`)
- a **range spec** per designed chain

It writes:

- `fixed_positions_jsonl` (one-line JSON dict):  
  `{ "<protein_name>": { "<chain>": [fixed_positions...] , ... } }`

---

## Requirements

- Python 3 (no extra dependencies)

---

## Usage

```bash
python fixseq.py \
  --parsed_jsonl parsed.jsonl \
  --out_jsonl fixed_positions.jsonl \
  --designed_chains "A" \
  --mode keep_fixed \
  --ranges "A:1-350,360-370,380-388"
````

After it runs, you’ll see:

```text
Wrote fixed_positions.jsonl
```

---

## How to plug into a typical ProteinMPNN workflow

### 1) Parse PDB(s) into `parsed.jsonl`

Using the official docker image example (adjust mounts/paths):

```bash
docker run --rm --gpus all \
  -v "$PWD":/inputs \
  --entrypoint python rosettacommons/proteinmpnn:latest \
  /app/proteinmpnn/helper_scripts/parse_multiple_chains.py \
  --input_path /inputs \
  --output_path /inputs/parsed.jsonl
```

### 2) Define which chains are designable (ProteinMPNN helper)

Example: only design chain `A`

```bash
docker run --rm --gpus all \
  -v "$PWD":/inputs \
  --entrypoint python rosettacommons/proteinmpnn:latest \
  /app/proteinmpnn/helper_scripts/assign_fixed_chains.py \
  --input_path /inputs/parsed.jsonl \
  --output_path /inputs/chains_to_design.jsonl \
  --chain_list "A"
```

### 3) Generate `fixed_positions.jsonl` with this script

Example A: **keep_fixed mode**

* The positions you list are **fixed** (NOT redesigned).
* Unlisted positions on designed chains become **designable**.

```bash
python fixseq.py \
  --parsed_jsonl parsed.jsonl \
  --out_jsonl fixed_positions.jsonl \
  --designed_chains "A" \
  --mode keep_fixed \
  --ranges "A:1-120,200-250"
```

Example B: **designable mode**

* The positions you list are **designable**.
* Everything else on designed chains becomes **fixed**.

```bash
python fixseq.py \
  --parsed_jsonl parsed.jsonl \
  --out_jsonl fixed_positions.jsonl \
  --designed_chains "A" \
  --mode designable \
  --ranges "A:35-70,90-110"
```

Example C: design the **whole chain** (special `*`)

* `A:*` means no fixed positions for chain A.

```bash
python fixseq.py \
  --parsed_jsonl parsed.jsonl \
  --out_jsonl fixed_positions.jsonl \
  --designed_chains "A" \
  --mode keep_fixed \
  --ranges "A:*"
```

### 4) Run ProteinMPNN with both JSONLs

```bash
docker run --rm --gpus all \
  -v "$PWD":/inputs \
  --entrypoint python rosettacommons/proteinmpnn:latest \
  /app/proteinmpnn/protein_mpnn_run.py \
  --jsonl_path /inputs/parsed.jsonl \
  --chain_id_jsonl /inputs/chains_to_design.jsonl \
  --fixed_positions_jsonl /inputs/fixed_positions.jsonl \
  --out_folder /inputs/mpnn_out \
  --num_seq_per_target 16 \
  --sampling_temp "0.1"
```

---

## CLI Arguments

### `--parsed_jsonl` (required)

Output of `parse_multiple_chains.py`.

### `--out_jsonl` (required)

Where to write the `fixed_positions_jsonl`.

### `--designed_chains` (required)

Space-separated chain IDs to be designed, e.g.:

* `"A"`
* `"A B"`

> Chain IDs must be **single character**: `[A-Za-z0-9_]`.

### `--mode` (optional)

* `keep_fixed` (default): the ranges you provide are **fixed**
* `designable`: the ranges you provide are **designable** (fixed = complement)

### `--ranges` (required)

Per-chain residue position specification.

---

## Range spec format

### Chain separator

Use `;` or `|` to separate chains:

* `A:1-10,20-30;B:5-8`
* `A:1-10 20-30 | B:5-8`

### Inside a chain

Use comma **or** whitespace:

* `1-3,7,10-12`
* `1-3 7 10-12`

### Special token

* `*` means whole chain (no fixed positions output)

Example:

* `A:*`
* `A:1-50;B:*`

---

## Important notes (read this if results look “wrong”)

1. **Positions are 1-indexed** and refer to the **sequence index in `parsed.jsonl`**
   Not the original PDB residue numbers.

2. If a chain is **NOT** in `--designed_chains`, this script writes `[]` for that chain.
   ProteinMPNN will treat it as a fixed chain when combined with `chains_to_design.jsonl`.

3. Every designed chain must appear in `--ranges`
   Otherwise the script will error out (to avoid silent mistakes).

---

## Troubleshooting

* `positions out of [1,L]`
  Your range includes indices outside the chain length in `parsed.jsonl`.
* `chain X is designed but not provided in --ranges`
  Add that chain to the `--ranges` spec.
* `invalid chain id`
  Chain IDs must be a **single** character like `A` / `B`.

---

This work is done at [Yang Lab](https://jieyang-lab.com/) at [UVA](https://www.virginia.edu/) school of medicine, [Department of Biochemistry-Molecular Genetics](https://med.virginia.edu/bmg/), under the supervision of [Prof.Jie Yang](https://med.virginia.edu/faculty/faculty-listing/wfw7nc/)
