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

# 職種カテゴリ分類
_CXO  = re.compile(
    r'(?<![a-zA-Z])(ceo|cfo|coo|cto|cmo|cpo|chro|cxo|cso|cdo|cro|vpoai|vpoe)(?![a-zA-Z])'
    r'|(?<![a-zA-Z])(vp\.?of|vp)(?![a-zA-Z])'
    r'|head\s*of'
    r'|取締役|執行役員|代表取締役|社長|会長|副社長',
    re.I)
_BIZDEV = re.compile(r'事業開発|bizdev|biz.?dev|新規事業|m&a|アライアンス|partnership|portfolio', re.I)
_HR     = re.compile(r'人事|(?<![a-zA-Z])hr(?![a-zA-Z])|hrbp|採用|労務|組織開発|リクルーター?|タレントマネ|ピープル', re.I)
_PR     = re.compile(r'広報|(?<![a-zA-Z])pr(?![a-zA-Z])|ブランディング|public.?relation', re.I)
_MKTG   = re.compile(r'マーケティング|マーケター|marketing|(?<![a-zA-Z])crm(?![a-zA-Z])|(?<![a-zA-Z])pmm(?![a-zA-Z])|グロース(?!マネ)|d2cマーケ|webマーケ|デジタルマーケ', re.I)
_KEIEI  = re.compile(r'経営企画|経営管理|事業戦略|経営戦略|(?<![a-zA-Z])pmo(?![a-zA-Z])|ir(?:室|長|担当)', re.I)
_SALES  = re.compile(r'営業|セールス|(?<![a-zA-Z])sales(?![a-zA-Z])|account.?manag|カスタマーサクセス|インサイドセールス|フィールドセールス|(?<![a-zA-Z])bdr(?![a-zA-Z])|(?<![a-zA-Z])cs(?![a-zA-Z])', re.I)
_ADMIN  = re.compile(r'総務|法務|財務|経理|管理部|バックオフィス|秘書|コンプライアンス|内部監査|オペレーション|ファイナンス', re.I)

def categorize_job(position, category=''):
    s = position + ' ' + (category or '')
    # 経営（CxO）は最優先 — ただし 経営企画 スタッフ職は除く
    if _CXO.search(s):
        if '経営企画' in s and not re.search(r'cfo|coo|ceo|cto|cmo|取締役|執行役員', s, re.I):
            return '経営企画'
        return '経営（CxO）'
    if _BIZDEV.search(s):  return '事業開発'
    if _HR.search(s):      return '人事'
    if _PR.search(s):      return '広報PR'
    if _MKTG.search(s):    return 'マーケティング'
    if _KEIEI.search(s):   return '経営企画'
    if _SALES.search(s):   return '営業系'
    if _ADMIN.search(s):   return '総務'
    return 'その他'

jobs_list = []
jobs_full = []

with open('C:/Users/furuy/Downloads/export_2026-04-11_22-22-12.csv',
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

        job_category = clean(row, '職種')

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
            'jobCat':     categorize_job(position, job_category),
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
            'selection':        clean(row, '選考ポイント'),
            'persona':          clean(row, '求める人材像'),
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
