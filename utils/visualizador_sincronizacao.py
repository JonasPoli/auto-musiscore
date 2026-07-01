#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
visualizador_sincronizacao.py
Servidor local para conferir e sincronizar as legendas (letras) dos hinos em MP3/JSON.
"""

import os
import sys
import json
import re
import shutil
import urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer
import socket
import webbrowser
import threading

PORT = 8000
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class LyricsEditorHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        # Evitar poluição do terminal com requisições estáticas
        pass

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        query = urllib.parse.parse_qs(parsed_url.query)

        if path == '/api/directories':
            self.handle_api_directories()
        elif path == '/api/files':
            self.handle_api_files(query)
        elif path == '/api/load':
            self.handle_api_load(query)
        elif path == '/api/audio':
            self.handle_api_audio(query)
        elif path == '/' or path == '/index.html':
            self.serve_html_page()
        else:
            # Fallback para arquivos estáticos se necessário (do SimpleHTTPRequestHandler)
            super().do_GET()

    def do_POST(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path

        if path == '/api/save':
            self.handle_api_save()
        else:
            self.send_error(404, "Endpoint não encontrado")

    # ==============================================================================
    # ENDPOINTS DA API
    # ==============================================================================

    def handle_api_directories(self):
        """Retorna uma lista de subdiretórios prováveis para busca no workspace."""
        dirs = []
        # Buscar recursivamente ou caminhos padrão conhecidos
        default_paths = [
            'output/meia_hora/orgao_eletronico_drawbar',
            'output/lyrics/brass',
            'output/lyrics/string'
        ]
        
        for dp in default_paths:
            full_p = os.path.join(WORKSPACE_ROOT, dp)
            if os.path.exists(full_p):
                dirs.append(dp)

        # Escanear outras subpastas em output
        search_roots = ['output']
        for s_root in search_roots:
            full_s_root = os.path.join(WORKSPACE_ROOT, s_root)
            if os.path.exists(full_s_root):
                for name in os.listdir(full_s_root):
                    sub_p = os.path.join(full_s_root, name)
                    if os.path.isdir(sub_p) and sub_p not in [os.path.join(WORKSPACE_ROOT, d) for d in default_paths]:
                        rel_p = os.path.relpath(sub_p, WORKSPACE_ROOT)
                        dirs.append(rel_p)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(dirs, ensure_ascii=False).encode('utf-8'))

    def handle_api_files(self, query):
        """Lista os arquivos JSON e confirma se possuem áudio MP3 correspondente."""
        dir_param = query.get('dir', [''])[0]
        if not dir_param:
            self.send_error(400, "Parâmetro 'dir' é obrigatório")
            return

        # Segurança: impedir navegação fora do workspace
        target_dir = os.path.abspath(os.path.join(WORKSPACE_ROOT, dir_param))
        if not target_dir.startswith(os.path.abspath(WORKSPACE_ROOT)):
            # Se for um caminho absoluto fora do workspace, mas válido no disco
            if not os.path.exists(target_dir):
                self.send_error(403, "Acesso proibido fora do workspace")
                return

        file_list = []
        if os.path.exists(target_dir) and os.path.isdir(target_dir):
            for filename in sorted(os.listdir(target_dir)):
                if filename.endswith('.json') and not filename.startswith('._'):
                    json_path = os.path.join(target_dir, filename)
                    mp3_name = filename.replace('.json', '.mp3')
                    mp3_path = os.path.join(target_dir, mp3_name)
                    has_mp3 = os.path.exists(mp3_path)

                    # Ler o título de dentro do JSON
                    titulo = filename
                    try:
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            titulo = f"{data.get('hino', '')} - {data.get('titulo', filename)}"
                    except Exception:
                        pass

                    file_list.append({
                        'filename': filename,
                        'json_path': os.path.relpath(json_path, WORKSPACE_ROOT),
                        'mp3_path': os.path.relpath(mp3_path, WORKSPACE_ROOT) if has_mp3 else None,
                        'titulo': titulo,
                        'has_mp3': has_mp3
                    })

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(file_list, ensure_ascii=False).encode('utf-8'))

    def handle_api_load(self, query):
        """Carrega um arquivo JSON."""
        path_param = query.get('path', [''])[0]
        if not path_param:
            self.send_error(400, "Parâmetro 'path' é obrigatório")
            return

        # Segurança: resolver caminho absoluto
        file_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path_param))
        if not os.path.exists(file_path) or not file_path.endswith('.json'):
            self.send_error(404, "Arquivo não encontrado")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(content, ensure_ascii=False).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Erro ao ler JSON: {str(e)}")

    def handle_api_audio(self, query):
        """Transmite o áudio MP3 suportando Range Requests."""
        path_param = query.get('path', [''])[0]
        if not path_param:
            self.send_error(400, "Parâmetro 'path' é obrigatório")
            return

        file_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path_param))
        if not os.path.exists(file_path) or not file_path.endswith('.mp3'):
            self.send_error(404, "Áudio não encontrado")
            return

        # Implementação de Range Request
        try:
            file_size = os.path.getsize(file_path)
        except OSError:
            self.send_error(404, "Arquivo não pôde ser lido")
            return

        range_header = self.headers.get('Range')
        start = 0
        end = file_size - 1
        is_range = False

        if range_header:
            match = re.match(r'bytes=(\d+)-(\d*)', range_header)
            if match:
                is_range = True
                start = int(match.group(1))
                if match.group(2):
                    end = int(match.group(2))

        if start >= file_size or end >= file_size or start > end:
            self.send_response(416)
            self.send_header('Content-Range', f'bytes */{file_size}')
            self.end_headers()
            return

        chunk_size = end - start + 1

        if is_range:
            self.send_response(206)
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
        else:
            self.send_response(200)

        self.send_header('Content-Type', 'audio/mpeg')
        self.send_header('Content-Length', str(chunk_size))
        self.send_header('Accept-Ranges', 'bytes')
        self.end_headers()

        try:
            with open(file_path, 'rb') as f:
                f.seek(start)
                bytes_to_send = chunk_size
                buffer_size = 64 * 1024
                while bytes_to_send > 0:
                    chunk = f.read(min(buffer_size, bytes_to_send))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    bytes_to_send -= len(chunk)
        except Exception:
            # Conexão fechada pelo navegador
            pass

    def handle_api_save(self):
        """Salva as alterações no arquivo JSON original, criando backup .bak."""
        content_length = int(self.headers.get('Content-Length', 0))
        if not content_length:
            self.send_error(400, "Corpo da requisição vazio")
            return

        try:
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            path_param = payload.get('path')
            letra_data = payload.get('letra')
            intro_duration = payload.get('intro_duration')

            if not path_param or letra_data is None:
                self.send_error(400, "Dados incompletos (path ou letra ausentes)")
                return

            file_path = os.path.abspath(os.path.join(WORKSPACE_ROOT, path_param))
            if not os.path.exists(file_path) or not file_path.endswith('.json'):
                self.send_error(404, "Arquivo JSON de destino não encontrado")
                return

            # Ler o original para manter as outras propriedades intactas
            with open(file_path, 'r', encoding='utf-8') as f:
                original_data = json.load(f)

            # Criar backup .bak
            bak_path = file_path + '.bak'
            shutil.copy2(file_path, bak_path)

            # Atualizar os tempos da letra
            original_data['letra'] = letra_data

            # Atualizar intro_duration
            if intro_duration is not None:
                original_data['intro_duration'] = float(intro_duration)

            # Salvar de volta de forma bonita
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(original_data, f, ensure_ascii=False, indent=2)

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success', 'backup': os.path.basename(bak_path)}).encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Erro ao salvar arquivo: {str(e)}")

    # ==============================================================================
    # SERVIR A INTERFACE DO USUÁRIO
    # ==============================================================================

    def serve_html_page(self):
        """Retorna o código HTML5/CSS3/JS da aplicação frontend."""
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()

        html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sincronizador de Letras 🎵</title>
    <!-- Google Fonts Inter -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-surface: #151d30;
            --bg-element: #1e293b;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.15);
            --accent-hover: #60a5fa;
            --success: #10b981;
            --warning: #f59e0b;
            --border: #334155;
            --sidebar-width: 320px;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            scrollbar-width: thin;
            scrollbar-color: var(--border) transparent;
        }

        /* Scrollbars */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: transparent;
        }
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }

        body {
            font-family: 'Inter', sans-serif;
            background-color: var(--bg-base);
            color: var(--text-primary);
            display: flex;
            height: 100vh;
            overflow: hidden;
        }

        /* Layout lateral */
        aside {
            width: var(--sidebar-width);
            background-color: var(--bg-surface);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            flex-shrink: 0;
        }

        .sidebar-header {
            padding: 20px;
            border-bottom: 1px solid var(--border);
        }

        .sidebar-header h1 {
            font-size: 1.1rem;
            font-weight: 700;
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }

        .dir-input-group {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
        }

        .dir-input-group select, .dir-input-group input {
            flex-grow: 1;
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-family: inherit;
        }

        .btn {
            background-color: var(--accent);
            color: white;
            border: none;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
        }

        .btn:hover {
            background-color: var(--accent-hover);
        }

        .btn-secondary {
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            color: var(--text-primary);
        }

        .btn-secondary:hover {
            background-color: var(--border);
        }

        .btn-success {
            background-color: var(--success);
        }

        .btn-success:hover {
            background-color: #059669;
        }

        .search-box {
            position: relative;
        }

        .search-box input {
            width: 100%;
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
        }

        .file-list {
            flex-grow: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .file-item {
            display: flex;
            flex-direction: column;
            padding: 12px;
            border-radius: 6px;
            cursor: pointer;
            margin-bottom: 8px;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }

        .file-item:hover {
            background-color: var(--bg-element);
        }

        .file-item.active {
            background-color: var(--accent-glow);
            border-color: var(--accent);
        }

        .file-item .file-title {
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .file-item .file-meta {
            font-size: 0.75rem;
            color: var(--text-secondary);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .badge {
            font-size: 0.65rem;
            padding: 2px 6px;
            border-radius: 4px;
            font-weight: 600;
        }

        .badge-success { background-color: rgba(16, 185, 129, 0.15); color: var(--success); }
        .badge-warning { background-color: rgba(245, 158, 11, 0.15); color: var(--warning); }
        .badge-error { background-color: rgba(239, 68, 68, 0.15); color: #f87171; }

        /* Workspace principal */
        main {
            flex-grow: 1;
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
            background-color: var(--bg-base);
        }

        .no-selection {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 100%;
            color: var(--text-muted);
            text-align: center;
            gap: 16px;
        }

        .no-selection-icon {
            font-size: 3rem;
        }

        .hymn-container {
            display: flex;
            flex-direction: column;
            height: 100%;
            overflow: hidden;
        }

        /* Top Bar: Player e Controle */
        .player-bar {
            background-color: var(--bg-surface);
            border-bottom: 1px solid var(--border);
            padding: 16px 24px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            z-index: 10;
        }

        .player-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .hymn-info h2 {
            font-size: 1.1rem;
            font-weight: 700;
        }

        .hymn-info p {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .player-controls {
            display: flex;
            align-items: center;
            gap: 16px;
            flex-wrap: wrap;
        }

        audio {
            flex-grow: 1;
            height: 36px;
            border-radius: 8px;
            background-color: var(--bg-element);
        }

        .speed-control {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.8rem;
            background-color: var(--bg-element);
            padding: 6px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
        }

        .speed-control select {
            background: transparent;
            border: none;
            color: var(--text-primary);
            font-weight: 600;
            outline: none;
            cursor: pointer;
        }

        /* Split-screen: Karaoke em cima, tabela em baixo */
        .workspace-split {
            display: flex;
            flex-direction: column;
            flex-grow: 1;
            overflow: hidden;
        }

        /* Painel Karaoke */
        .karaoke-panel {
            background-color: #0f172a;
            border-bottom: 1px solid var(--border);
            padding: 30px 24px;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            min-height: 180px;
            position: relative;
            overflow: hidden;
            box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.4);
        }

        .lyrics-pre {
            font-size: 0.95rem;
            color: var(--text-muted);
            margin-bottom: 12px;
            opacity: 0.5;
            transition: all 0.3s ease;
        }

        .lyrics-active {
            font-size: 1.6rem;
            font-weight: 700;
            color: #60a5fa;
            text-shadow: 0 0 15px rgba(59, 130, 246, 0.4);
            margin-bottom: 12px;
            transition: all 0.3s ease;
            transform: scale(1.02);
        }

        .lyrics-active.lyrics-intro {
            color: #fbbf24; /* Cor amarela âmbar para introdução */
            text-shadow: 0 0 15px rgba(245, 158, 11, 0.4);
            animation: pulse-glow 2s infinite;
        }

        .lyrics-active.lyrics-pause {
            color: var(--text-muted);
            text-shadow: none;
            font-style: italic;
        }

        @keyframes pulse-glow {
            0%, 100% { opacity: 0.8; transform: scale(1); }
            50% { opacity: 1; transform: scale(1.02); }
        }

        .lyrics-post {
            font-size: 1.1rem;
            color: var(--text-secondary);
            opacity: 0.7;
            transition: all 0.3s ease;
        }

        /* Editor de Tabela */
        .table-panel {
            flex-grow: 1;
            overflow-y: auto;
            padding: 20px 24px;
            background-color: var(--bg-base);
        }

        .table-actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
        }

        .bulk-shift-panel {
            display: flex;
            align-items: center;
            gap: 8px;
            background-color: var(--bg-surface);
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid var(--border);
        }

        .bulk-shift-panel span {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .bulk-shift-panel input[type="number"] {
            width: 70px;
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8rem;
            text-align: center;
        }

        .editor-table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.85rem;
        }

        .editor-table th {
            color: var(--text-secondary);
            font-weight: 600;
            padding: 10px 12px;
            border-bottom: 1px solid var(--border);
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .editor-table tr {
            border-bottom: 1px solid rgba(51, 65, 85, 0.5);
            transition: background-color 0.15s ease;
        }

        .editor-table tr:hover {
            background-color: rgba(30, 41, 59, 0.4);
        }

        .editor-table tr.active {
            background-color: rgba(59, 130, 246, 0.08);
            border-left: 3px solid var(--accent);
        }

        .editor-table td {
            padding: 10px 12px;
            vertical-align: middle;
        }

        .col-index { width: 50px; color: var(--text-muted); font-family: 'JetBrains Mono', monospace; }
        .col-type { width: 70px; }
        .col-text { min-width: 250px; font-weight: 500; }
        .col-time { width: 190px; }
        .col-actions { width: 280px; text-align: right; }

        .time-input-group {
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .time-input {
            width: 75px;
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 6px 8px;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.8rem;
            text-align: center;
            outline: none;
        }

        .time-input:focus {
            border-color: var(--accent);
            box-shadow: 0 0 0 1px var(--accent);
        }

        .btn-sm {
            padding: 4px 8px;
            font-size: 0.75rem;
            border-radius: 4px;
        }

        .btn-icon {
            width: 28px;
            height: 28px;
            padding: 0;
            border-radius: 4px;
        }

        .adjust-btn {
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-family: 'JetBrains Mono', monospace;
        }

        .adjust-btn:hover {
            background-color: var(--border);
            color: var(--text-primary);
        }

        .capture-btn {
            background-color: rgba(59, 130, 246, 0.1);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: var(--accent-hover);
        }

        .capture-btn:hover {
            background-color: var(--accent);
            color: white;
        }

        /* Keyboard Info */
        .footer-info {
            background-color: var(--bg-surface);
            border-top: 1px solid var(--border);
            padding: 10px 24px;
            font-size: 0.75rem;
            color: var(--text-muted);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .keyboard-shortcuts {
            display: flex;
            gap: 16px;
        }

        .shortcut {
            display: inline-flex;
            align-items: center;
            gap: 4px;
        }

        kbd {
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            border-radius: 3px;
            padding: 1px 5px;
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-primary);
            font-size: 0.7rem;
            box-shadow: 0 1px 0 rgba(0,0,0,0.2);
        }

        .toast {
            position: fixed;
            bottom: 60px;
            right: 20px;
            background-color: var(--bg-element);
            border: 1px solid var(--border);
            border-left: 4px solid var(--accent);
            padding: 12px 20px;
            border-radius: 6px;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            gap: 10px;
            box-shadow: 0 10px 25px -5px rgba(0,0,0,0.5);
            z-index: 1000;
            opacity: 0;
            transform: translateY(10px);
            transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
        }

        .toast.show {
            opacity: 1;
            transform: translateY(0);
        }

        .toast.success { border-left-color: var(--success); }
        .toast.error { border-left-color: #f87171; }
    </style>
</head>
<body>

    <!-- SIDEBAR -->
    <aside>
        <div class="sidebar-header">
            <h1>🎵 Sincro Hinos</h1>
            <div class="dir-input-group">
                <select id="dirSelect" onchange="loadFiles()">
                    <option value="">Carregando pastas...</option>
                </select>
                <button class="btn btn-secondary btn-icon" onclick="scanDirectories()" title="Recarregar pastas">🔄</button>
            </div>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Buscar hino por nome/número..." oninput="filterFiles()">
            </div>
        </div>
        <div class="file-list" id="fileList">
            <!-- Arquivos serão inseridos aqui -->
        </div>
    </aside>

    <!-- WORKSPACE -->
    <main>
        <!-- Estado inicial sem hino selecionado -->
        <div id="noSelectionView" class="no-selection">
            <div class="no-selection-icon">🎼</div>
            <h3>Nenhum Hino Selecionado</h3>
            <p>Selecione um hino na barra lateral para começar a verificar a legenda.</p>
        </div>

        <!-- Interface de sincronização -->
        <div id="hymnView" class="hymn-container" style="display: none;">
            
            <!-- PLAYER BAR -->
            <div class="player-bar">
                <div class="player-header">
                    <div class="hymn-info" style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
                        <div>
                            <h2 id="currentHymnTitle">Carregando...</h2>
                            <p id="currentHymnFile">Nome do arquivo</p>
                        </div>
                        <div id="introDurationPanel" style="display: flex; align-items: center; gap: 8px; background-color: var(--bg-element); padding: 8px 12px; border-radius: 6px; border: 1px solid var(--border); margin-left: 10px;">
                            <span style="font-size: 0.8rem; color: var(--text-secondary); font-weight: 500;">⏱️ Introdução:</span>
                            <button class="btn btn-secondary btn-sm adjust-btn" style="padding: 2px 6px;" onclick="adjustIntro(-0.5)">-0.5s</button>
                            <button class="btn btn-secondary btn-sm adjust-btn" style="padding: 2px 6px;" onclick="adjustIntro(-0.1)">-0.1s</button>
                            <input type="text" class="time-input" id="introDurationInput" value="0.000" onchange="onIntroInputChange(this.value)" style="width: 70px; padding: 4px 6px;">
                            <button class="btn btn-secondary btn-sm adjust-btn" style="padding: 2px 6px;" onclick="adjustIntro(0.1)">+0.1s</button>
                            <button class="btn btn-secondary btn-sm adjust-btn" style="padding: 2px 6px;" onclick="adjustIntro(0.5)">+0.5s</button>
                            <button class="btn btn-sm capture-btn" style="padding: 2px 8px;" onclick="captureIntro()" title="Define o fim da introdução até o tempo atual do áudio (Atalho I)">Definir Atual [I]</button>
                        </div>
                    </div>
                    <div style="display:flex; gap: 10px;">
                        <button class="btn btn-success" onclick="saveLyrics()">💾 Salvar JSON</button>
                    </div>
                </div>

                <div class="player-controls">
                    <audio id="audioPlayer" controls></audio>
                    
                    <div class="speed-control">
                        <span>Velocidade:</span>
                        <select id="playbackSpeed" onchange="changePlaybackSpeed()">
                            <option value="0.5">0.5x</option>
                            <option value="0.7">0.7x (Muito Lento)</option>
                            <option value="0.8">0.8x (Lento)</option>
                            <option value="0.9">0.9x</option>
                            <option value="1.0" selected>1.0x (Normal)</option>
                            <option value="1.1">1.1x</option>
                            <option value="1.2">1.2x</option>
                            <option value="1.5">1.5x</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- SPLIT WORKSPACE -->
            <div class="workspace-split">
                <!-- Modo Karaoke -->
                <div class="karaoke-panel">
                    <div class="lyrics-pre" id="karaokePre">...</div>
                    <div class="lyrics-active" id="karaokeActive">Reproduza o áudio para ver as legendas</div>
                    <div class="lyrics-post" id="karaokePost">...</div>
                </div>

                <!-- Tabela de Edição -->
                <div class="table-panel">
                    <div class="table-actions">
                        <h3>Editor de Timestamps</h3>
                        
                        <!-- Ajuste em lote -->
                        <div class="bulk-shift-panel">
                            <span>Ajuste em lote:</span>
                            <input type="number" id="shiftAmount" step="0.05" value="0.00" title="Tempo em segundos (ex: 0.1 para +100ms, -0.2 para -200ms)">
                            <span>s</span>
                            <button class="btn btn-secondary btn-sm" onclick="applyBulkShift('all')">Todas as Linhas</button>
                            <button class="btn btn-secondary btn-sm" onclick="applyBulkShift('onwards')">Desta Linha em Diante</button>
                        </div>
                    </div>

                    <table class="editor-table">
                        <thead>
                            <tr>
                                <th class="col-index">#</th>
                                <th class="col-type">Tipo</th>
                                <th class="col-text">Texto</th>
                                <th class="col-time">Início (s)</th>
                                <th class="col-time">Fim (s)</th>
                                <th class="col-actions">Ações / Atalhos</th>
                            </tr>
                        </thead>
                        <tbody id="lyricsTableBody">
                            <!-- Inserido dinamicamente -->
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- FOOTER INFO -->
            <div class="footer-info">
                <div class="keyboard-shortcuts">
                    <span class="shortcut"><kbd>Espaço</kbd> Play/Pause</span>
                    <span class="shortcut"><kbd>←</kbd> / <kbd>→</kbd> -5s / +5s</span>
                    <span class="shortcut"><kbd>↑</kbd> / <kbd>↓</kbd> Navegar linhas</span>
                    <span class="shortcut"><kbd>I</kbd> Definir Fim da Intro</span>
                    <span class="shortcut"><kbd>S</kbd> Definir Início</span>
                    <span class="shortcut"><kbd>D</kbd> Definir Fim</span>
                </div>
                <div>
                    Backup automático criado ao salvar (.json.bak)
                </div>
            </div>

        </div>
    </main>

    <!-- TOAST NOTIFICATION -->
    <div id="toast" class="toast">
        <span id="toastIcon">ℹ️</span>
        <span id="toastMessage">Mensagem informativa</span>
    </div>

    <script>
        let allDirectories = [];
        let allFiles = [];
        let activeHymnData = null;
        let activeFileObj = null;
        let activeLineIndex = 0;
        let isModified = false;

        const audioPlayer = document.getElementById('audioPlayer');

        // Inicialização
        window.addEventListener('DOMContentLoaded', () => {
            scanDirectories();
            setupKeyboardShortcuts();
            
            // Listener do áudio para atualizar destaque
            audioPlayer.addEventListener('timeupdate', () => {
                updateHighlight();
            });
        });

        // ==============================================================================
        // INTEGRAÇÃO COM BACKEND API
        // ==============================================================================
        
        function scanDirectories() {
            fetch('/api/directories')
                .then(r => r.json())
                .then(dirs => {
                    allDirectories = dirs;
                    const select = document.getElementById('dirSelect');
                    select.innerHTML = '';
                    
                    if (dirs.length === 0) {
                        select.innerHTML = '<option value="">Nenhuma pasta padrão encontrada</option>';
                        return;
                    }

                    dirs.forEach(d => {
                        const opt = document.createElement('option');
                        opt.value = d;
                        opt.textContent = d;
                        select.appendChild(opt);
                    });
                    
                    loadFiles();
                })
                .catch(err => {
                    showToast('Erro ao listar diretórios: ' + err, 'error');
                });
        }

        function loadFiles() {
            const dir = document.getElementById('dirSelect').value;
            if (!dir) return;

            fetch(`/api/files?dir=${encodeURIComponent(dir)}`)
                .then(r => r.json())
                .then(files => {
                    allFiles = files;
                    filterFiles();
                })
                .catch(err => {
                    showToast('Erro ao carregar arquivos da pasta: ' + err, 'error');
                });
        }

        function filterFiles() {
            const query = document.getElementById('searchInput').value.toLowerCase();
            const list = document.getElementById('fileList');
            list.innerHTML = '';

            const filtered = allFiles.filter(f => 
                f.filename.toLowerCase().includes(query) || 
                f.titulo.toLowerCase().includes(query)
            );

            if (filtered.length === 0) {
                list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.8rem; padding: 12px;">Nenhum arquivo encontrado</div>';
                return;
            }

            filtered.forEach(f => {
                const item = document.createElement('div');
                item.className = 'file-item';
                if (activeFileObj && activeFileObj.json_path === f.json_path) {
                    item.className += ' active';
                }
                
                const title = document.createElement('span');
                title.className = 'file-title';
                title.textContent = f.titulo;
                
                const meta = document.createElement('div');
                meta.className = 'file-meta';
                
                const typeText = f.mp3_path ? 'Áudio OK' : 'Sem Áudio';
                const badgeClass = f.mp3_path ? 'badge-success' : 'badge-error';
                meta.innerHTML = `<span>${f.filename}</span> <span class="badge ${badgeClass}">${typeText}</span>`;
                
                item.appendChild(title);
                item.appendChild(meta);
                
                item.addEventListener('click', () => selectHymn(f));
                list.appendChild(item);
            });
        }

        function selectHymn(fileObj) {
            if (isModified) {
                if (!confirm("Você possui alterações não salvas. Deseja sair mesmo assim?")) {
                    return;
                }
            }

            activeFileObj = fileObj;
            
            // Re-renderizar lista para atualizar item ativo
            const items = document.querySelectorAll('.file-item');
            items.forEach(el => el.classList.remove('active'));
            
            // Carregar JSON
            fetch(`/api/load?path=${encodeURIComponent(fileObj.json_path)}`)
                .then(r => r.json())
                .then(data => {
                    activeHymnData = data;
                    isModified = false;
                    renderWorkspace();
                })
                .catch(err => {
                    showToast('Erro ao abrir JSON do hino: ' + err, 'error');
                });
        }

        // ==============================================================================
        // RENDER DO WORKSPACE
        // ==============================================================================
        
        function renderWorkspace() {
            document.getElementById('noSelectionView').style.display = 'none';
            document.getElementById('hymnView').style.display = 'flex';
            
            document.getElementById('currentHymnTitle').textContent = `${activeHymnData.hino} - ${activeHymnData.titulo}`;
            document.getElementById('currentHymnFile').textContent = activeFileObj.filename;
            
            // Configurar áudio
            if (activeFileObj.mp3_path) {
                audioPlayer.src = `/api/audio?path=${encodeURIComponent(activeFileObj.mp3_path)}`;
                audioPlayer.load();
            } else {
                audioPlayer.src = '';
                showToast('Aviso: Áudio MP3 não encontrado para este hino.', 'warning');
            }

            // Reset do speed selector
            document.getElementById('playbackSpeed').value = "1.0";
            audioPlayer.playbackRate = 1.0;

            // Inicializar duração da introdução
            document.getElementById('introDurationInput').value = (activeHymnData.intro_duration || 0).toFixed(3);

            // Renderizar tabela de letras
            renderTable();
            
            // Inicializar variáveis de destaque
            activeLineIndex = 0;
            updateHighlight();
        }

        function adjustIntro(delta) {
            if (!activeHymnData) return;
            activeHymnData.intro_duration = Math.max(0, (activeHymnData.intro_duration || 0) + delta);
            document.getElementById('introDurationInput').value = activeHymnData.intro_duration.toFixed(3);
            isModified = true;
            markFileAsModified();
            updateHighlight();
        }

        function onIntroInputChange(value) {
            if (!activeHymnData) return;
            const floatVal = parseFloat(value);
            if (isNaN(floatVal) || floatVal < 0) {
                showToast("Por favor, insira um valor de tempo válido para a introdução.", "error");
                document.getElementById('introDurationInput').value = (activeHymnData.intro_duration || 0).toFixed(3);
                return;
            }
            activeHymnData.intro_duration = floatVal;
            isModified = true;
            markFileAsModified();
            updateHighlight();
        }

        function captureIntro() {
            if (!activeHymnData) return;
            const currentTime = audioPlayer.currentTime;
            activeHymnData.intro_duration = currentTime;
            document.getElementById('introDurationInput').value = currentTime.toFixed(3);
            isModified = true;
            markFileAsModified();
            updateHighlight();
            showToast(`Duração da introdução definida para: ${currentTime.toFixed(3)}s`, "success");
        }

        function renderTable() {
            const tbody = document.getElementById('lyricsTableBody');
            tbody.innerHTML = '';

            if (!activeHymnData.letra || activeHymnData.letra.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding: 20px;">Nenhuma frase cadastrada no JSON</td></tr>';
                return;
            }

            activeHymnData.letra.forEach((line, index) => {
                const tr = document.createElement('tr');
                tr.id = `tr-${index}`;
                tr.setAttribute('data-index', index);
                if (index === activeLineIndex) {
                    tr.className = 'active';
                }

                // Coluna índice
                const tdIndex = document.createElement('td');
                tdIndex.className = 'col-index';
                tdIndex.textContent = `${line.num_verso || 1}.${line.num_linha || (index + 1)}`;
                tr.appendChild(tdIndex);

                // Coluna Tipo
                const tdType = document.createElement('td');
                tdType.className = 'col-type';
                tdType.textContent = line.tipo || 'verso';
                tr.appendChild(tdType);

                // Coluna Texto
                const tdText = document.createElement('td');
                tdText.className = 'col-text';
                tdText.textContent = line.texto;
                tr.appendChild(tdText);

                // Coluna Início
                const tdInicio = document.createElement('td');
                tdInicio.className = 'col-time';
                tdInicio.innerHTML = `
                    <div class="time-input-group">
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'inicio', -0.5)">-0.5s</button>
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'inicio', -0.1)">-0.1s</button>
                        <input type="text" class="time-input" id="inicio-${index}" value="${line.inicio.toFixed(3)}" onchange="onTimeInputChange(${index}, 'inicio', this.value)">
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'inicio', 0.1)">+0.1s</button>
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'inicio', 0.5)">+0.5s</button>
                    </div>
                `;
                tr.appendChild(tdInicio);

                // Coluna Fim
                const tdFim = document.createElement('td');
                tdFim.className = 'col-time';
                tdFim.innerHTML = `
                    <div class="time-input-group">
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'fim', -0.5)">-0.5s</button>
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'fim', -0.1)">-0.1s</button>
                        <input type="text" class="time-input" id="fim-${index}" value="${line.fim.toFixed(3)}" onchange="onTimeInputChange(${index}, 'fim', this.value)">
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'fim', 0.1)">+0.1s</button>
                        <button class="btn btn-secondary btn-sm adjust-btn" onclick="adjustTime(${index}, 'fim', 0.5)">+0.5s</button>
                    </div>
                `;
                tr.appendChild(tdFim);

                // Coluna Ações
                const tdActions = document.createElement('td');
                tdActions.className = 'col-actions';
                tdActions.innerHTML = `
                    <button class="btn btn-secondary btn-sm" onclick="seekTo(${line.inicio})" title="Ouvir esta frase">▶️ Ouvir</button>
                    <button class="btn btn-sm capture-btn" onclick="captureTime(${index}, 'inicio')" title="Define o tempo atual como o início (Atalho S)">[ Início</button>
                    <button class="btn btn-sm capture-btn" onclick="captureTime(${index}, 'fim')" title="Define o tempo atual como o fim (Atalho D)">Fim ]</button>
                `;
                tr.appendChild(tdActions);

                // Clique na linha seleciona a linha
                tr.addEventListener('click', (e) => {
                    // Evitar seleção caso clique nos inputs ou botões
                    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'BUTTON') {
                        changeActiveLine(index);
                    }
                });

                tbody.appendChild(tr);
            });
        }

        // ==============================================================================
        // LÓGICA DE EDIÇÃO & CONTROLE DE TEMPO
        // ==============================================================================

        function changeActiveLine(index) {
            if (index < 0 || index >= activeHymnData.letra.length) return;
            
            // Remover destaque da linha anterior
            const prevTr = document.getElementById(`tr-${activeLineIndex}`);
            if (prevTr) prevTr.classList.remove('active');
            
            activeLineIndex = index;
            
            // Adicionar destaque na nova linha
            const newTr = document.getElementById(`tr-${activeLineIndex}`);
            if (newTr) {
                newTr.classList.add('active');
                // Scroll para manter a linha visível na tabela se necessário
                newTr.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }

            // Atualizar modo Karaoke
            updateKaraokePanel();
        }

        function adjustTime(index, field, delta) {
            const line = activeHymnData.letra[index];
            if (!line) return;

            line[field] = Math.max(0, line[field] + delta);
            
            // Atualizar input
            const input = document.getElementById(`${field}-${index}`);
            if (input) {
                input.value = line[field].toFixed(3);
            }
            
            isModified = true;
            updateKaraokePanel();
            markFileAsModified();
        }

        function onTimeInputChange(index, field, value) {
            const floatVal = parseFloat(value);
            if (isNaN(floatVal) || floatVal < 0) {
                showToast("Por favor, insira um valor de tempo numérico válido.", "error");
                // Reverter input
                document.getElementById(`${field}-${index}`).value = activeHymnData.letra[index][field].toFixed(3);
                return;
            }

            activeHymnData.letra[index][field] = floatVal;
            isModified = true;
            updateKaraokePanel();
            markFileAsModified();
        }

        function captureTime(index, field) {
            const currentTime = audioPlayer.currentTime;
            const line = activeHymnData.letra[index];
            if (!line) return;

            line[field] = currentTime;
            
            const input = document.getElementById(`${field}-${index}`);
            if (input) {
                input.value = currentTime.toFixed(3);
            }

            isModified = true;
            updateKaraokePanel();
            markFileAsModified();
            showToast(`Tempo de ${field} capturado: ${currentTime.toFixed(3)}s`, "success");
        }

        function seekTo(time) {
            audioPlayer.currentTime = time;
            audioPlayer.play();
        }

        function changePlaybackSpeed() {
            const speed = parseFloat(document.getElementById('playbackSpeed').value);
            audioPlayer.playbackRate = speed;
        }

        // ==============================================================================
        // DESLOCAMENTO EM LOTE (SHIFT)
        // ==============================================================================

        function applyBulkShift(mode) {
            const shiftAmountVal = parseFloat(document.getElementById('shiftAmount').value);
            if (isNaN(shiftAmountVal) || shiftAmountVal === 0) {
                showToast("Especifique um valor de deslocamento diferente de zero.", "error");
                return;
            }

            let startIdx = 0;
            if (mode === 'onwards') {
                startIdx = activeLineIndex;
                if (!confirm(`Deseja deslocar as legendas de ${shiftAmountVal > 0 ? '+' : ''}${shiftAmountVal}s da linha ${startIdx + 1} em diante?`)) {
                    return;
                }
            } else {
                if (!confirm(`Deseja deslocar TODAS as legendas do hino em ${shiftAmountVal > 0 ? '+' : ''}${shiftAmountVal}s?`)) {
                    return;
                }
            }

            for (let i = startIdx; i < activeHymnData.letra.length; i++) {
                const line = activeHymnData.letra[i];
                line.inicio = Math.max(0, line.inicio + shiftAmountVal);
                line.fim = Math.max(0, line.fim + shiftAmountVal);

                // Atualizar na interface
                const startInput = document.getElementById(`inicio-${i}`);
                const endInput = document.getElementById(`fim-${i}`);
                if (startInput) startInput.value = line.inicio.toFixed(3);
                if (endInput) endInput.value = line.fim.toFixed(3);
            }

            isModified = true;
            updateKaraokePanel();
            markFileAsModified();
            showToast(`Deslocamento em lote de ${shiftAmountVal}s aplicado com sucesso.`, "success");
            // Resetar o input
            document.getElementById('shiftAmount').value = "0.00";
        }

        // ==============================================================================
        // CONTROLE DO KARAOKE (HIGHLIGHT EM TEMPO REAL)
        // ==============================================================================

        function updateHighlight() {
            if (!activeHymnData || !activeHymnData.letra) return;
            
            const time = audioPlayer.currentTime;
            let currentIdx = -1;
            let introDuration = activeHymnData.intro_duration || 0;

            if (time < introDuration) {
                // Introdução ativa
                currentIdx = -2;
            } else {
                // Tenta achar a linha tocando agora
                for (let i = 0; i < activeHymnData.letra.length; i++) {
                    const line = activeHymnData.letra[i];
                    if (time >= line.inicio && time <= line.fim) {
                        currentIdx = i;
                        break;
                    }
                }
                
                // Se está em pausa, acha a próxima linha para destacar no editor
                if (currentIdx === -1) {
                    for (let i = 0; i < activeHymnData.letra.length; i++) {
                        if (time < activeHymnData.letra[i].inicio) {
                            currentIdx = i;
                            break;
                        }
                    }
                    if (currentIdx === -1) {
                        currentIdx = activeHymnData.letra.length - 1;
                    }
                }
            }

            // Se encontrou uma linha ativa diferente da selecionada, navega
            if (currentIdx !== -1 && currentIdx !== -2 && currentIdx !== activeLineIndex) {
                changeActiveLine(currentIdx);
            } else {
                updateKaraokePanel(currentIdx);
            }
        }

        function updateKaraokePanel(currentIdxOverride) {
            if (!activeHymnData || !activeHymnData.letra || activeHymnData.letra.length === 0) return;

            const time = audioPlayer.currentTime;
            const introDuration = activeHymnData.intro_duration || 0;
            const activeEl = document.getElementById('karaokeActive');
            
            // Se currentIdxOverride não foi passado, calcular
            let stateIdx = currentIdxOverride !== undefined ? currentIdxOverride : -1;
            if (stateIdx === -1) {
                if (time < introDuration) {
                    stateIdx = -2;
                } else {
                    for (let i = 0; i < activeHymnData.letra.length; i++) {
                        const line = activeHymnData.letra[i];
                        if (time >= line.inicio && time <= line.fim) {
                            stateIdx = i;
                            break;
                        }
                    }
                }
            }

            if (stateIdx === -2) {
                // Introdução
                document.getElementById('karaokePre').textContent = " ";
                activeEl.textContent = "[ Introdução ]";
                activeEl.className = 'lyrics-active lyrics-intro';
                activeEl.style.color = '';
                activeEl.style.textShadow = '';
                document.getElementById('karaokePost').textContent = activeHymnData.letra[0].texto;
                
                // Remover destaque da linha na tabela se estiver na intro
                const activeTr = document.querySelector('.editor-table tr.active');
                if (activeTr) activeTr.classList.remove('active');
                return;
            }

            const line = activeHymnData.letra[activeLineIndex];
            
            const preVal = activeLineIndex > 0 ? activeHymnData.letra[activeLineIndex - 1].texto : "";
            const postVal = activeLineIndex < activeHymnData.letra.length - 1 ? activeHymnData.letra[activeLineIndex + 1].texto : "";

            document.getElementById('karaokePre').textContent = preVal || " ";
            document.getElementById('karaokePost').textContent = postVal || " ";

            // Verificar se o tempo atual do áudio está exatamente no intervalo da linha selecionada
            if (time >= line.inicio && time <= line.fim) {
                activeEl.textContent = line.texto;
                activeEl.className = 'lyrics-active';
                activeEl.style.color = '';
                activeEl.style.textShadow = '';
            } else {
                // Se está em silêncio/pausa
                activeEl.textContent = "[ Pausa ]";
                activeEl.className = 'lyrics-active lyrics-pause';
                activeEl.style.color = '';
                activeEl.style.textShadow = '';
            }
        }

        // ==============================================================================
        // ATALHOS DE TECLADO E SALVAR
        // ==============================================================================

        function setupKeyboardShortcuts() {
            document.addEventListener('keydown', (e) => {
                // Se o foco estiver em um input de texto, ignorar atalhos globais
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
                    // Atalho Enter nos campos de tempo para salvar foco
                    if (e.key === 'Enter') {
                        e.target.blur();
                    }
                    return;
                }

                if (e.key === ' ') {
                    e.preventDefault(); // Impedir scroll da página
                    if (audioPlayer.paused) {
                        audioPlayer.play();
                    } else {
                        audioPlayer.pause();
                    }
                } else if (e.key === 'ArrowLeft') {
                    audioPlayer.currentTime = Math.max(0, audioPlayer.currentTime - 5);
                } else if (e.key === 'ArrowRight') {
                    audioPlayer.currentTime = Math.min(audioPlayer.duration || 9999, audioPlayer.currentTime + 5);
                } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    if (activeLineIndex > 0) {
                        changeActiveLine(activeLineIndex - 1);
                    }
                } else if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    if (activeLineIndex < activeHymnData.letra.length - 1) {
                        changeActiveLine(activeLineIndex + 1);
                    }
                } else if (e.key.toLowerCase() === 's') {
                    captureTime(activeLineIndex, 'inicio');
                } else if (e.key.toLowerCase() === 'd') {
                    captureTime(activeLineIndex, 'fim');
                } else if (e.key.toLowerCase() === 'i') {
                    captureIntro();
                }
            });
        }

        // Registrar atalho Cmd+S ou Ctrl+S para salvar
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 's') {
                e.preventDefault();
                saveLyrics();
            }
        });

        function saveLyrics() {
            if (!activeHymnData) return;

            fetch('/api/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    path: activeFileObj.json_path,
                    letra: activeHymnData.letra,
                    intro_duration: activeHymnData.intro_duration || 0
                })
            })
            .then(r => r.json())
            .then(res => {
                if (res.status === 'success') {
                    showToast(`Sincronização salva com sucesso! Backup: ${res.backup}`, 'success');
                    isModified = false;
                    unmarkFileAsModified();
                } else {
                    showToast(`Erro ao salvar: ${res.message || 'Erro desconhecido'}`, 'error');
                }
            })
            .catch(err => {
                showToast(`Falha na requisição de salvamento: ${err}`, 'error');
            });
        }

        function markFileAsModified() {
            const h2 = document.getElementById('currentHymnTitle');
            if (h2 && !h2.textContent.endsWith(' *')) {
                h2.textContent += ' *';
            }
        }

        function unmarkFileAsModified() {
            const h2 = document.getElementById('currentHymnTitle');
            if (h2 && h2.textContent.endsWith(' *')) {
                h2.textContent = h2.textContent.substring(0, h2.textContent.length - 2);
            }
        }

        // ==============================================================================
        // TOASTS E AUXILIARES
        // ==============================================================================

        function showToast(message, type = 'info') {
            const toast = document.getElementById('toast');
            const messageEl = document.getElementById('toastMessage');
            const iconEl = document.getElementById('toastIcon');

            messageEl.textContent = message;
            
            if (type === 'success') {
                iconEl.textContent = '✅';
                toast.className = 'toast success show';
            } else if (type === 'error') {
                iconEl.textContent = '❌';
                toast.className = 'toast error show';
            } else if (type === 'warning') {
                iconEl.textContent = '⚠️';
                toast.className = 'toast warning show';
            } else {
                iconEl.textContent = 'ℹ️';
                toast.className = 'toast show';
            }

            setTimeout(() => {
                toast.classList.remove('show');
            }, 3000);
        }
    </script>
</body>
</html>
"""
        self.wfile.write(html.encode('utf-8'))

def get_free_port(start_port=8000):
    port = start_port
    while port < 9000:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                port += 1
    return start_port

def start_server(port):
    server = HTTPServer(('127.0.0.1', port), LyricsEditorHandler)
    print(f"\n==================================================")
    print(f" Servidor iniciado com sucesso!")
    print(f" Abra no seu navegador:")
    print(f"    http://127.0.0.1:{port}/")
    print(f"==================================================\n")
    print("Pressione Ctrl+C para encerrar o servidor.")
    
    # Abre navegador automaticamente
    webbrowser.open_new_tab(f"http://127.0.0.1:{port}/")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrando o servidor...")
        server.server_close()

if __name__ == '__main__':
    # Entrar no diretório raiz do projeto
    os.chdir(WORKSPACE_ROOT)
    
    port = get_free_port(PORT)
    start_server(port)
