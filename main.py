import json
import sqlite3
import sys

import openpyxl


def get_kodansha_kanji():
    wb = openpyxl.load_workbook("kodansha_kanji_list.xlsx")
    sh = wb.active
    l = []
    for row in range(2, 2302):
        l.append(sh.cell(row=row, column=2).value)
    return l


def get_kanji2viet_dict():
    kanjis = get_kodansha_kanji()
    k2v = {k: None for k in kanjis}
    with open("./kanji2viet.jsonl", encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            x = json.loads(line)
            kanji = x["KANJI"]
            viet = x["VIỆT"].lower()
            k2v[kanji] = viet

    # look at the rest in phienam.txt
    with open("phienam.txt") as f:
        for line in f:
            toks = line.strip().split("=")
            if len(toks) != 2:
                continue
            kanji, viet = toks
            if kanji in k2v and k2v[kanji] is None:
                k2v[kanji] = viet

    return k2v


def get_cognates():
    cognates = {}
    with open("chinese-hanviet-cognates.tsv") as f:
        for idx, line in enumerate(f):
            if idx == 0:
                continue
            toks = line.strip().split("\t")
            if not toks:
                continue
            kanji_word = toks[3]
            viet = toks[5]
            cognates[kanji_word] = viet
    return cognates


if __name__ == "__main__":
    # TODO: automatically unzip apkg & return sqlite file.
    # too lazy rn...
    k2v = get_kanji2viet_dict()
    cognates = get_cognates()
    sqlite_file = sys.argv[1]
    conn = sqlite3.connect(sqlite_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * from notes")
    cmds = []
    # learn this fact from https://github.com/patarapolw/ankisync2
    sep = "\x1f"
    for row in cursor:
        id = row[0]
        flds = row[6].split(sep)
        if len(flds) == 40:
            kanji = flds[2].strip()
            keyword = flds[3]
            if kanji in k2v:
                keyword = keyword + f", {k2v[kanji]}"
            flds[3] = keyword
        else:
            kanji = flds[4].strip()
            meaning = flds[2]
            l = list(kanji)
            while l and l[-1] not in k2v:
                l.pop()
            l = "".join(l)
            if l in cognates:
                meaning += f", {cognates[l]}"
            else:
                tmp = []
                for k in kanji:
                    if k in k2v and k2v[k] is not None:
                        v = k2v[k].split(",")
                        v = [x.strip() for x in v]
                        v = "/".join(v)
                        tmp.append(f"{v}")
                if tmp:
                    meaning += f", {'-'.join(tmp)}"
            flds[2] = meaning
        flds = sep.join(flds)
        cmd = "UPDATE notes SET flds = ? WHERE id = ?"
        params = [flds, id]
        cmds.append((cmd, params))

    for cmd, params in cmds:
        # pardon my ignorance, first time using sqlite
        cursor = conn.cursor()
        cursor.execute(cmd, params)
        conn.commit()
    conn.close()
