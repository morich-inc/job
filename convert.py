# -*- coding: utf-8 -*-
import csv, json, re, sys
sys.stdout.reconfigure(encoding='utf-8')

PLACEHOLDER = re.compile(r'[〇○×△▲＊\*]+万|〇円|〇〜|応相談のみ|給与詳細参照')

def clean(row, key, maxlen=None):
    v = (row.get(key) or '').strip()
    v = re.sub(r'\r\n|\r', '\n', v)
    v = re.sub(r'\n{3,}', '\n\n', v)
    return v[:maxlen] if maxlen else v

def first_line(row, key, maxlen=60):
    return clean(row, key).split('\n')[0][:maxlen].strip()

def clean_salary(s):
    s = s.split('\n')[0][:80].strip()
    return '' if (PLACEHOLDER.search(s) or not s) else s

def clean_hq(s):
    """郵便番号プレフィックスを除去して住所だけ残す"""
    s = s.split('\n')[0].strip()
    s = re.sub(r'^〒\d{3}-?\d{4}[\s　]*', '', s).strip()
    return s[:80]

def clean_comment(s):
    """▼記載方針・URLなど内部メモ行を除去"""
    if not s:
        return ''
    lines = []
    skip_block = False
    for line in s.split('\n'):
        stripped = line.strip()
        # ▼記載方針 ブロック開始 → 次の ■ が来るまでスキップ
        if stripped.startswith('▼記載方針'):
            skip_block = True
            continue
        if skip_block:
            if stripped.startswith('■'):
                skip_block = False
            else:
                continue
        # URLのみの行は除去
        if re.match(r'^https?://\S+$', stripped):
            continue
        # 「記載しない」系の行を除去
        if re.search(r'記載しない|非公開のため|開示不可', stripped):
            continue
        lines.append(line)
    result = '\n'.join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result).strip()
    return result

def recommend_short(s, maxlen=100):
    lines = [l.strip() for l in s.split('\n') if l.strip()]
    return ' '.join(lines[:2])[:maxlen]

# ざっくり職種 → フィルタータブ のマッピング
SHOKUSHU_MAP = {
    '経営人材（CEO／COO）': '経営（CxO）',
    'CFO':                  '経営（CxO）',
    '事業部長':              '経営（CxO）',
    '社外役員／監査役':       '経営（CxO）',
    '経営企画／M&A':         '経営企画',
    'IR':                   '経営企画',
    '人事':                  '人事',
    'マーケティング':         'マーケティング',
    '広報・PR':               '広報PR',
    '新規事業開発・事業企画':  '事業開発',
    '営業':                   '営業系',
    '営業企画':               '営業系',
    'カスタマーサクセス':      '営業系',
    '総務':                   '総務',
    '法務':                   '総務',
    '経理財務':               '総務',
    '内部監査':               '総務',
    '管理部長':               '総務',
    '秘書・アシスタント':     '総務',
    'CTO／ITエンジニア':      'その他',
    'CIO／社内SE':            'その他',
    'コンサルタント':          'その他',
    'プロダクトマネージャー':  'その他',
    'プロジェクトマネージャー':'その他',
    '商品企画':               'その他',
    'その他':                 'その他',
    '副業希望（業務委託OK）':  'その他',
}

def parse_jobcats(raw):
    """ざっくり職種（カンマ区切り）→ フィルタータブのリスト（重複除去）"""
    if not raw or not raw.strip():
        return ['その他']
    items = [v.strip() for v in raw.split(',') if v.strip()]
    cats = []
    for item in items:
        mapped = SHOKUSHU_MAP.get(item, 'その他')
        if mapped not in cats:
            cats.append(mapped)
    return cats if cats else ['その他']

jobs_list = []
jobs_full = []

with open('C:/Users/furuy/Downloads/export_2026-04-13_09-07-18.csv',
          encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        jid = clean(row, 'JOB ID')
        if not jid:
            continue

        position = clean(row, 'ポジション')

        # 「打診」は除外
        if position == '打診':
            continue

        salary = clean_salary(clean(row, '給与(詳細)'))
        hq = clean_hq(clean(row, '本社所在地'))

        # 一覧用
        jobs_list.append({
            'id':         jid,
            'company':    clean(row, '企業名'),
            'industry':   clean(row, '業種'),
            'stock':      first_line(row, '株式公開'),
            'position':   position,
            'employment': first_line(row, '雇用形態'),
            'location':   first_line(row, '勤務地'),
            'salary':     salary,
            'remote':     first_line(row, 'リモートワーク制度'),
            'sideJob':    clean(row, '副業可', 10),
            'rec':        recommend_short(clean(row, '★morichのオススメPOINT！')),
            'jobCats':    parse_jobcats(clean(row, 'ざっくり職種')),
        })

        # 詳細用
        jobs_full.append({
            'id':               jid,
            'company':          clean(row, '企業名'),
            'industry':         clean(row, '業種'),
            'stock':            first_line(row, '株式公開'),
            'ipo':              first_line(row, 'IPOフェーズ'),
            'position':         position,
            'category':         clean(row, '職種', 60),
            'employment':       clean(row, '雇用形態'),
            'location':         clean(row, '勤務地'),
            'locationDetail':   clean(row, '勤務地(詳細)'),
            'salary':           salary,
            'salaryDetail':     clean(row, '給与(詳細)'),
            'remote':           clean(row, 'リモートワーク制度'),
            'sideJob':          clean(row, '副業可', 10),
            'hq':               hq,
            'employees':        first_line(row, '従業員数'),
            'capital':          first_line(row, '資本金'),
            'founded':          first_line(row, '会社設立日'),
            'companyDesc':      clean(row, '事業内容・会社の特長'),
            'recommend':        clean(row, '★morichのオススメPOINT！'),
            'desc':             clean(row, '業務内容'),
            'reqSummary':       clean(row, '応募資格(概要)'),
            'reqDetail':        clean(row, '応募資格(詳細)'),
            'background':       clean(row, '募集背景'),
            'backgroundDetail': clean(row, '募集背景(詳細)'),
            'persona':          clean(row, '求める人物像'),
            'welfare':          clean(row, '待遇・福利厚生'),
            'holiday':          clean(row, '休日休暇'),
            'workHours':        clean(row, '勤務時間'),
            'smoking':          first_line(row, '喫煙環境について'),
        })

print(f'変換完了: {len(jobs_list)}件（打診除外済み）', file=sys.stderr)

with open('jobs-list.json', 'w', encoding='utf-8') as f:
    json.dump(jobs_list, f, ensure_ascii=False, separators=(',', ':'))

with open('jobs.json', 'w', encoding='utf-8') as f:
    json.dump(jobs_full, f, ensure_ascii=False, separators=(',', ':'))

import os
print(f'jobs-list.json: {os.path.getsize("jobs-list.json"):,} bytes', file=sys.stderr)
print(f'jobs.json:      {os.path.getsize("jobs.json"):,} bytes', file=sys.stderr)
