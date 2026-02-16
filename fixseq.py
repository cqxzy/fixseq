#!/usr/bin/env python3
import argparse, json, os, re, sys

def die(msg: str):
    print(f"wrong input type: {msg}", file=sys.stderr)
    sys.exit(2)

def parse_chain_spec(s: str):
    """
    支持：
      "A:1-10,20-30;B:5-8"
      "A:1-10 20-30 | B:5-8"
    分隔链用 ; 或 |，链内分隔片段用 逗号或空格。
    """
    s = (s or "").strip()
    if not s:
        return {}
    items = re.split(r"[;|]+", s)
    out = {}
    for item in items:
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            die(f"range item '{item}' missing ':' (expect like A:1-10,20-30)")
        ch, rr = item.split(":", 1)
        ch = ch.strip()
        rr = rr.strip()
        if not re.fullmatch(r"[A-Za-z0-9_]", ch):
            die(f"invalid chain id '{ch}' (expect single character like A/B)")
        out[ch] = rr
    return out

def parse_ranges(r: str):
    """
    支持：
      "1-3,7,10-12"
      "1-3 7 10-12"
      "1-3, 7, 10-12"
    返回 set(int)
    """
    r = (r or "").strip()
    if r == "" or r == "*":
        return set(), (r == "*")
    parts = re.split(r"[,\s]+", r)
    out = set()
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if not re.fullmatch(r"\d+(-\d+)?", p):
            die(f"bad range token '{p}' (expect 'N' or 'N-M')")
        if "-" in p:
            a, b = p.split("-", 1)
            a, b = int(a), int(b)
            if a > b:
                a, b = b, a
            out.update(range(a, b + 1))
        else:
            out.add(int(p))
    return out, False

def main():
    ap = argparse.ArgumentParser(
        description="Create ProteinMPNN fixed_positions_jsonl from parsed.jsonl using range specs."
    )
    ap.add_argument("--parsed_jsonl", required=True, help="output of parse_multiple_chains.py")
    ap.add_argument("--out_jsonl", required=True, help="fixed_positions_jsonl to write")
    ap.add_argument("--designed_chains", required=True, help='e.g. "A" or "A B"')
    ap.add_argument("--mode", choices=["designable", "keep_fixed"], default="keep_fixed",
                    help="keep_fixed: ranges are fixed; designable: ranges are designable (fixed = complement)")
    ap.add_argument("--ranges", required=True,
                    help='e.g. "A:1-350,360-370,380-388" or "A:*" or "A:1-10;B:5-8"')
    args = ap.parse_args()

    designed = args.designed_chains.split()
    if not designed:
        die("--designed_chains is empty")

    spec = parse_chain_spec(args.ranges)
    if not spec:
        die("--ranges parsed empty")

    out_dict = {}

    with open(args.parsed_jsonl, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            name = rec.get("name", None)
            if not name:
                die("parsed.jsonl missing 'name' field")

            # chains present in this target
            chains = []
            for k in rec.keys():
                if k.startswith("seq_chain_"):
                    chains.append(k.split("seq_chain_")[1])
            if not chains:
                die(f"{name}: no seq_chain_* fields found")

            fixed_pos_dict = {}

            for ch in chains:
                seq = rec.get(f"seq_chain_{ch}", "")
                L = len(seq)
                if L <= 0:
                    die(f"{name} chain {ch}: empty sequence length")

                # 非设计链：固定位置留空（MPNN 会把整条链当成 fixed chain）
                if ch not in designed:
                    fixed_pos_dict[ch] = []
                    continue

                rr = spec.get(ch, None)
                if rr is None:
                    die(f"{name}: chain {ch} is designed but not provided in --ranges")

                chosen, is_star = parse_ranges(rr)

                # '*'：全链设计（keep_fixed 模式下表示 fixed 为空；designable 模式下同理）
                if is_star:
                    fixed_pos_dict[ch] = []
                    continue

                # 边界检查
                bad = [x for x in chosen if x < 1 or x > L]
                if bad:
                    die(f"{name} chain {ch}: positions out of [1,{L}], e.g. {bad[:10]}")

                if args.mode == "keep_fixed":
                    fixed = chosen
                else:
                    fixed = set(range(1, L + 1)) - chosen

                fixed_pos_dict[ch] = sorted(fixed)

            out_dict[name] = fixed_pos_dict

    with open(args.out_jsonl, "w") as f:
        f.write(json.dumps(out_dict) + "\n")

    print(f"Wrote {args.out_jsonl}")

if __name__ == "__main__":
    main()
