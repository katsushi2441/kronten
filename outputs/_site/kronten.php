<?php
/**
 * Kurage 論点AIマップ（kronten）の公開入口。https://kurage.exbridge.jp/kronten.php/
 *
 * 地図は手元（scripts/publish.py）で HTML と JSON まで作り、kronten_data/ に置く。
 * このファイルは「置いたページを返す」「MCP に答える」「サイトマップを出す」だけで、AI は呼ばない。
 *
 *   /                 一覧（kronten_data/index.html）
 *   /about            作り方・MCP
 *   /t/<slug>/        テーマごとの地図（kronten_data/t_<slug>.html）
 *   /mcp              MCP（Streamable HTTP・JSON-RPC・読み取り専用・セッションなし）
 *   /sitemap.xml
 */
const KR_BASE = 'https://kurage.exbridge.jp/kronten.php';
$KR_DIR = __DIR__ . '/kronten_data';

$path = isset($_SERVER['PATH_INFO']) ? $_SERVER['PATH_INFO'] : '/';
$path = '/' . trim($path, '/');

function kr_send_html($file) {
    if (!is_file($file)) { kr_404(); }
    header('Content-Type: text/html; charset=utf-8');
    readfile($file);
    exit;
}

function kr_404() {
    http_response_code(404);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><title>見つかりません</title><p>ページが見つかりません。<a href="' . KR_BASE . '/">論点AIマップの一覧へ</a></p>';
    exit;
}

function kr_maps($dir) {
    $out = array();
    foreach (glob($dir . '/maps/*.json') as $f) {
        $m = json_decode(file_get_contents($f), true);
        if (is_array($m)) { $out[basename($f, '.json')] = $m; }
    }
    return $out;
}

/* ---------------- MCP ---------------- */

const KR_NOTE = '話題の名前・要約・論点はAI（gemma4）の要約で、代表的な声と元の発言で確かめる必要がある。件数は声のかたまりの数で、人数ではない。国会の発言は国会会議録検索システム、ネットの声は X の投稿と Yahoo!ニュースのコメント。';

function kr_tools() {
    $ro = array('readOnlyHint' => true, 'openWorldHint' => false);
    return array(
        array('name' => 'list_maps', 'title' => '論点AIマップの一覧',
              'description' => '公開している論点AIマップ（テーマごと）の一覧。slug・テーマ・件数・話題の数・作成日を返す。',
              'inputSchema' => array('type' => 'object', 'properties' => new stdClass(), 'additionalProperties' => false),
              'annotations' => $ro + array('title' => '論点AIマップの一覧')),
        array('name' => 'get_map', 'title' => 'テーマの話題と論点',
              'description' => '1つのテーマについて、話題（まとまり）ごとの名前・要約・論点（賛否を問える文）・件数・出典の内訳（国会の質疑/政府答弁/X/ニュースのコメント）を返す。',
              'inputSchema' => array('type' => 'object', 'properties' => array('slug' => array('type' => 'string', 'description' => 'list_maps の slug（例: kodomo-sns）')),
                                     'required' => array('slug'), 'additionalProperties' => false),
              'annotations' => $ro + array('title' => 'テーマの話題と論点')),
        array('name' => 'get_topic', 'title' => '話題の代表的な声',
              'description' => '1つの話題について、代表的な声（本文・出典・発言者・日付・元の発言のURL）と、会派・年ごとの件数を返す。topic は get_map の no（1から）。',
              'inputSchema' => array('type' => 'object', 'properties' => array(
                  'slug' => array('type' => 'string'), 'topic' => array('type' => 'integer', 'minimum' => 1)),
                  'required' => array('slug', 'topic'), 'additionalProperties' => false),
              'annotations' => $ro + array('title' => '話題の代表的な声')),
        array('name' => 'search_propositions', 'title' => '論点を語で探す',
              'description' => 'すべてのテーマの論点（賛否を問える文）と話題の名前から、語を含むものを探す。',
              'inputSchema' => array('type' => 'object', 'properties' => array('q' => array('type' => 'string', 'description' => '探す語（例: 年齢制限）')),
                                     'required' => array('q'), 'additionalProperties' => false),
              'annotations' => $ro + array('title' => '論点を語で探す')),
    );
}

function kr_text($data) {
    $data['note'] = KR_NOTE;
    return array('content' => array(array('type' => 'text', 'text' => json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES))));
}

function kr_err($msg) {
    return array('content' => array(array('type' => 'text', 'text' => $msg)), 'isError' => true);
}

function kr_call($name, $args, $dir) {
    $maps = kr_maps($dir);
    if ($name === 'list_maps') {
        $list = array();
        foreach ($maps as $s => $m) {
            $list[] = array('slug' => $s, 'theme' => $m['theme'], 'n' => $m['n'], 'topics' => $m['k'],
                            'built_at' => isset($m['built_at']) ? $m['built_at'] : '', 'url' => KR_BASE . '/t/' . $s . '/');
        }
        return kr_text(array('maps' => $list));
    }
    if ($name === 'get_map' || $name === 'get_topic') {
        $s = isset($args['slug']) ? (string)$args['slug'] : '';
        if (!isset($maps[$s])) { return kr_err('slug が見つかりません。list_maps で確かめてください: ' . $s); }
        $m = $maps[$s];
        if ($name === 'get_map') {
            $topics = array();
            foreach ($m['clusters'] as $i => $c) {
                $topics[] = array('no' => $i + 1, 'name' => $c['name'], 'summary' => $c['summary'], 'propositions' => $c['propositions'],
                                  'size' => $c['size'], 'by_source' => $c['by_source']);
            }
            return kr_text(array('theme' => $m['theme'], 'n' => $m['n'], 'sources' => $m['sources'], 'topics' => $topics,
                                 'url' => KR_BASE . '/t/' . $s . '/'));
        }
        $no = isset($args['topic']) ? (int)$args['topic'] : 0;
        if ($no < 1 || $no > count($m['clusters'])) { return kr_err('topic は 1〜' . count($m['clusters']) . ' で指定してください'); }
        $c = $m['clusters'][$no - 1];
        return kr_text(array('theme' => $m['theme'], 'no' => $no, 'name' => $c['name'], 'summary' => $c['summary'],
                             'propositions' => $c['propositions'], 'by_source' => $c['by_source'], 'by_group' => $c['by_group'],
                             'by_year' => $c['by_year'], 'quotes' => $c['quotes'], 'url' => KR_BASE . '/t/' . $s . '/#t' . $c['id']));
    }
    if ($name === 'search_propositions') {
        $q = trim(isset($args['q']) ? (string)$args['q'] : '');
        if ($q === '') { return kr_err('q（探す語）を入れてください'); }
        $hits = array();
        foreach ($maps as $s => $m) {
            foreach ($m['clusters'] as $i => $c) {
                $props = array_values(array_filter($c['propositions'], function ($p) use ($q) { return mb_strpos($p, $q) !== false; }));
                if ($props || mb_strpos($c['name'], $q) !== false) {
                    $hits[] = array('slug' => $s, 'theme' => $m['theme'], 'no' => $i + 1, 'topic' => $c['name'],
                                    'propositions' => $props ? $props : $c['propositions'], 'size' => $c['size']);
                }
            }
        }
        return kr_text(array('q' => $q, 'hits' => array_slice($hits, 0, 30)));
    }
    return null;
}

function kr_handle($msg, $dir) {
    if (!is_array($msg) || !isset($msg['jsonrpc']) || $msg['jsonrpc'] !== '2.0' || !isset($msg['method'])) {
        return array('jsonrpc' => '2.0', 'id' => null, 'error' => array('code' => -32600, 'message' => 'Invalid Request'));
    }
    if (!array_key_exists('id', $msg)) { return null; }   // 通知には答えない
    $id = $msg['id'];
    $method = $msg['method'];
    $params = isset($msg['params']) && is_array($msg['params']) ? $msg['params'] : array();
    $versions = array('2025-06-18', '2025-03-26', '2024-11-05');
    if ($method === 'initialize') {
        $want = isset($params['protocolVersion']) ? $params['protocolVersion'] : '';
        $res = array('protocolVersion' => in_array($want, $versions, true) ? $want : $versions[0],
                     'capabilities' => array('tools' => array('listChanged' => false)),
                     'serverInfo' => array('name' => 'kronten', 'title' => 'Kurage 論点AIマップ', 'version' => '1.0.0', 'websiteUrl' => KR_BASE . '/'),
                     'instructions' => 'Kurage 論点AIマップ（株式会社エクスブリッジ）の MCP です。国会の発言とネットの声から作った、テーマごとの話題と論点（賛否を問える文）を返します。答えるときは、出典の内訳と元の発言の URL を示し、話題の名前と論点はAIの要約であることを伝えてください。');
    } elseif ($method === 'ping') {
        $res = new stdClass();
    } elseif ($method === 'tools/list') {
        $res = array('tools' => kr_tools());
    } elseif ($method === 'tools/call') {
        $res = kr_call(isset($params['name']) ? $params['name'] : '', isset($params['arguments']) && is_array($params['arguments']) ? $params['arguments'] : array(), $dir);
        if ($res === null) {
            return array('jsonrpc' => '2.0', 'id' => $id, 'error' => array('code' => -32602, 'message' => 'Unknown tool'));
        }
    } elseif ($method === 'resources/list' || $method === 'prompts/list') {
        $res = array(explode('/', $method)[0] => array());
    } else {
        return array('jsonrpc' => '2.0', 'id' => $id, 'error' => array('code' => -32601, 'message' => 'Method not found: ' . $method));
    }
    return array('jsonrpc' => '2.0', 'id' => $id, 'result' => $res);
}

if ($path === '/mcp') {
    header('Content-Type: application/json; charset=utf-8');
    if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
        http_response_code(405);
        header('Allow: POST');
        echo json_encode(array('error' => 'POST で JSON-RPC を送ってください。使い方: ' . KR_BASE . '/about#mcp'), JSON_UNESCAPED_UNICODE);
        exit;
    }
    $msg = json_decode(file_get_contents('php://input'), true);
    if ($msg === null) {
        http_response_code(400);
        echo json_encode(array('jsonrpc' => '2.0', 'id' => null, 'error' => array('code' => -32700, 'message' => 'Parse error')));
        exit;
    }
    if (isset($msg[0])) {
        $out = array();
        foreach ($msg as $m) { $r = kr_handle($m, $KR_DIR); if ($r !== null) { $out[] = $r; } }
        if (!$out) { http_response_code(202); exit; }
        echo json_encode($out, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        exit;
    }
    $r = kr_handle($msg, $KR_DIR);
    if ($r === null) { http_response_code(202); exit; }
    echo json_encode($r, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

if ($path === '/sitemap.xml') {
    header('Content-Type: application/xml; charset=utf-8');
    echo '<?xml version="1.0" encoding="UTF-8"?>' . "\n" . '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">';
    $top = 0;
    foreach (kr_maps($KR_DIR) as $s => $m) {
        $d = substr(isset($m['built_at']) ? $m['built_at'] : '', 0, 10);
        if ($d > $top) { $top = $d; }
        echo '<url><loc>' . KR_BASE . '/t/' . htmlspecialchars($s) . '/</loc>' . ($d ? '<lastmod>' . $d . '</lastmod>' : '') . '</url>';
    }
    echo '<url><loc>' . KR_BASE . '/</loc>' . ($top ? '<lastmod>' . $top . '</lastmod>' : '') . '</url>';
    echo '<url><loc>' . KR_BASE . '/about</loc></url></urlset>';
    exit;
}

if ($path === '/') { kr_send_html($KR_DIR . '/index.html'); }
if ($path === '/about') { kr_send_html($KR_DIR . '/about.html'); }
if (preg_match('#^/t/([a-z0-9-]+)$#', $path, $mm)) { kr_send_html($KR_DIR . '/t_' . $mm[1] . '.html'); }
kr_404();
