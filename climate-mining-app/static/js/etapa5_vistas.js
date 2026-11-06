// ClimaTec - Etapa 5 / Vistas de analisis multidimensional.
// Cada vista consulta el modelo estrella (SQLite) a traves de /api/etapa5/olap.
// Toda cifra que se muestra (indicadores, graficas y matriz) viene de una consulta
// al modelo: los cambios de nivel (drill-down / roll-up) piden al servidor una
// nueva agregacion, de modo que las medidas se recalculan en SQL en cada nivel.
// Operaciones: slice y dice (filtros), drill-down y roll-up (cambio de nivel en
// una jerarquia), pivot (intercambio de filas y columnas de la matriz).
// Sin librerias externas: DOM y SVG.

(function () {
    'use strict';

    var nodoCfg = document.getElementById('e5-config');
    if (!nodoCfg) return;
    var CFG = JSON.parse(nodoCfg.textContent);
    var NS = 'http://www.w3.org/2000/svg';
    var C_FRIO = '#49c7e0', C_CALIDO = '#ff6a4d', C_AMBAR = '#ffb454', C_OK = '#3ddc97', C_MORADO = '#c9b6ff';
    var PALETA = [C_FRIO, C_AMBAR, C_OK, C_MORADO, '#7aa2ff', '#f08bd0'];

    // ---- Utilidades -----------------------------------------------------------
    function el(id) { return document.getElementById(id); }
    function q(sel, base) { return (base || document).querySelector(sel); }
    function vaciar(n) { while (n && n.firstChild) n.removeChild(n.firstChild); }
    function crear(tag, clase, texto) {
        var n = document.createElement(tag);
        if (clase) n.className = clase;
        if (texto !== undefined && texto !== null) n.textContent = texto;
        return n;
    }
    function svg(tag, attrs) {
        var n = document.createElementNS(NS, tag);
        Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
        return n;
    }
    function dec(n, d) { return Number(n).toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d }); }
    function auto(n) {
        if (n === null || n === undefined || isNaN(n)) return '—';
        var a = Math.abs(n);
        if (a >= 1e9) return dec(n / 1e9, 2) + ' mil M';
        if (a >= 1e6) return dec(n / 1e6, 1) + ' M';
        if (a >= 100) return dec(n, 0);
        if (a >= 10) return dec(n, 1);
        return dec(n, 2);
    }
    function pct(n, d) { return n === null || isNaN(n) ? '—' : dec(n, d === undefined ? 1 : d) + '%'; }
    function signo(n, d, suf) { return n === null || isNaN(n) ? '—' : (n > 0 ? '+' : '') + dec(n, d === undefined ? 1 : d) + (suf === undefined ? '%' : suf); }
    function opcion(sel, valor, texto) { var o = crear('option', '', texto); o.value = valor; sel.appendChild(o); return o; }
    function campo(caja, etiqueta, nodo, ancho) {
        var l = crear('label', 'pob-campo');
        if (ancho) l.style.maxWidth = ancho;
        l.appendChild(crear('span', '', etiqueta));
        l.appendChild(nodo);
        caja.appendChild(l);
        return nodo;
    }
    function selector(caja, etiqueta, opciones, valor, alCambiar, ancho) {
        var s = crear('select');
        opciones.forEach(function (o) { opcion(s, o[0], o[1]); });
        s.value = valor;
        s.addEventListener('change', function () { alCambiar(s.value); });
        return campo(caja, etiqueta, s, ancho);
    }
    function casillas(caja, etiqueta, opciones, marcados, alCambiar) {
        var l = crear('div', 'pob-campo');
        l.style.maxWidth = 'none';
        l.appendChild(crear('span', '', etiqueta));
        var c = crear('div', 'e5-checks');
        opciones.forEach(function (o) {
            var lab = crear('label', 'e5-check');
            var i = crear('input'); i.type = 'checkbox'; i.value = o[0]; i.checked = marcados.indexOf(o[0]) >= 0;
            i.addEventListener('change', function () {
                var sel = Array.prototype.filter.call(c.querySelectorAll('input'), function (x) { return x.checked; })
                    .map(function (x) { return x.value; });
                alCambiar(sel);
            });
            lab.appendChild(i); lab.appendChild(crear('span', '', o[1])); c.appendChild(lab);
        });
        l.appendChild(c); caja.appendChild(l);
        return c;
    }
    function boton(caja, texto, accion, titulo) {
        var b = crear('button', 'pob-reset', texto); b.type = 'button';
        if (titulo) b.title = titulo;
        b.addEventListener('click', accion);
        caja.appendChild(b);
        return b;
    }
    function segmentos(caja, etiqueta, opciones, valor, alCambiar) {
        var l = crear('div', 'pob-campo e5-campo-seg');
        l.appendChild(crear('span', '', etiqueta));
        var s = crear('div', 'e5-seg'); s.setAttribute('role', 'radiogroup');
        var bs = opciones.map(function (o) {
            var b = crear('button', '', o[1]); b.type = 'button'; b.dataset.v = o[0]; b.setAttribute('role', 'radio');
            b.addEventListener('click', function () { if (!b.disabled) alCambiar(o[0]); });
            s.appendChild(b); return b;
        });
        l.appendChild(s); caja.appendChild(l);
        return {
            marcar: function (v, deshabilitados) {
                bs.forEach(function (b) {
                    var act = b.dataset.v === String(v);
                    b.classList.toggle('activo', act); b.setAttribute('aria-checked', act ? 'true' : 'false');
                    b.disabled = (deshabilitados || []).indexOf(b.dataset.v) >= 0;
                });
            }
        };
    }

    // ---- Tooltip ---------------------------------------------------------------
    var tip = crear('div', 'pob-tip'); tip.setAttribute('role', 'tooltip'); tip.style.display = 'none';
    document.body.appendChild(tip);
    function verTip(e, t) {
        tip.textContent = t; tip.style.display = 'block';
        var x = e.clientX, y = e.clientY;
        if (!x && e.target.getBoundingClientRect) { var r = e.target.getBoundingClientRect(); x = r.left + r.width / 2; y = r.top; }
        tip.style.left = Math.min(x + 14, window.innerWidth - 290) + 'px'; tip.style.top = (y + 14) + 'px';
    }
    function ocultarTip() { tip.style.display = 'none'; }
    function conTip(n, t, accion) {
        n.setAttribute('tabindex', '0'); n.setAttribute('aria-label', t);
        n.addEventListener('mousemove', function (e) { verTip(e, t); });
        n.addEventListener('mouseleave', ocultarTip);
        n.addEventListener('focus', function (e) { verTip(e, t); });
        n.addEventListener('blur', ocultarTip);
        if (accion) {
            n.style.cursor = 'pointer';
            n.addEventListener('click', function () { ocultarTip(); accion(); });
            n.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ocultarTip(); accion(); } });
        }
    }

    // ---- Consultas al modelo -------------------------------------------------
    var consultasHechas = [];
    function api(titulo, filas, columnas, medida, filtros) {
        var p = ['filas=' + encodeURIComponent(filas), 'medida=' + encodeURIComponent(medida)];
        if (columnas) p.push('columnas=' + encodeURIComponent(columnas));
        Object.keys(filtros || {}).forEach(function (a) {
            (filtros[a] || []).forEach(function (v) { p.push('f=' + encodeURIComponent(a + '=' + v)); });
        });
        return fetch(CFG.api + '?' + p.join('&')).then(function (r) {
            return r.json().then(function (j) {
                if (!r.ok) throw new Error(j.error || 'Error en la consulta');
                consultasHechas.push({ titulo: titulo, sql: j.sql, n: j.n_hechos });
                return j;
            });
        });
    }
    function celda(r, f, c) { var v = r.celdas[f + '|' + (c === undefined || c === null ? '' : c)]; return v === undefined ? null : v; }
    function totalFila(r, f) { var v = r.total_filas[String(f)]; return v === undefined ? null : v; }
    function totalCol(r, c) { var v = r.total_columnas[String(c)]; return v === undefined ? null : v; }

    // ---- Estado comun: seleccion activa, consultas, KPIs ----------------------
    function seleccion(chips) {
        var c = el('e5-sel'); vaciar(c);
        chips.forEach(function (x) {
            var s = crear('span', 'e5-chip op-' + x.op);
            s.appendChild(crear('b', '', x.etq));
            s.appendChild(document.createTextNode(x.texto));
            c.appendChild(s);
        });
    }
    function mostrarConsultas() {
        var c = el('e5-consultas'); vaciar(c);
        consultasHechas.forEach(function (x) {
            c.appendChild(crear('p', 'e5-consulta-tit', x.titulo + ' · ' + dec(x.n, 0) + ' hechos'));
            var pre = crear('pre', 'e5-codigo'); pre.appendChild(crear('code', '', x.sql)); c.appendChild(pre);
        });
    }
    function kpi(i, valor, etiqueta, sub) {
        var k = el('k' + i);
        q('.valor', k).textContent = valor;
        q('.etiqueta', k).textContent = etiqueta;
        q('.pob-ind-sub', k).textContent = sub || '';
    }
    function grafica(i, titulo, sub) {
        var g = el('g' + i);
        q('.e5-g-tit', g).textContent = titulo;
        q('.e5-g-sub', g).textContent = sub || '';
        var ley = q('.e5-g-ley', g); vaciar(ley);
        var cuerpo = q('.e5-g-cuerpo', g); vaciar(cuerpo);
        return { cuerpo: cuerpo, ley: ley };
    }
    function leyenda(ley, items) {
        items.forEach(function (x) {
            var s = crear('span'); var i = crear('i', 'pob-sw'); i.style.background = x.color;
            s.appendChild(i); s.appendChild(document.createTextNode(' ' + x.nombre)); ley.appendChild(s);
        });
    }
    function estado(msg) { el('e5-estado').textContent = msg || ''; }
    function ciclo(fn) {
        consultasHechas = [];
        document.body.classList.add('e5-cargando');
        estado('');
        return fn().then(function () { mostrarConsultas(); })
            .catch(function (e) { estado(e.message); })
            .then(function () { document.body.classList.remove('e5-cargando'); });
    }

    // ---- Graficas --------------------------------------------------------------
    // Lineas: cats [{clave, etiqueta}], series [{nombre, color, valores{clave: v}}]
    function lineas(caja, cats, series, unidad, opc) {
        opc = opc || {};
        var vals = [];
        series.forEach(function (s) { cats.forEach(function (c) { var v = s.valores[c.clave]; if (v !== null && v !== undefined) vals.push(v); }); });
        if (!vals.length) { caja.appendChild(crear('p', 'pob-mini', 'Sin datos para esta seleccion.')); return; }
        var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
        if (opc.base !== undefined) { mn = Math.min(mn, opc.base); mx = Math.max(mx, opc.base); }
        var pad = (mx - mn) * 0.12 || Math.abs(mx) * 0.1 || 1; mn -= pad; mx += pad;
        var W = 640, H = 300, L = 58, R = 14, T = 24, B = 40;
        var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, class: 'pob-svg', width: '100%' });
        function X(i) { return cats.length === 1 ? (L + W - R) / 2 : L + i * (W - L - R) / (cats.length - 1); }
        function Y(v) { return T + (mx - v) / (mx - mn) * (H - T - B); }
        for (var g = 0; g <= 4; g++) {
            var v = mn + (mx - mn) * g / 4;
            s.appendChild(svg('line', { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: 'e5-grid' }));
            var t = svg('text', { x: L - 6, y: Y(v) + 4, 'text-anchor': 'end', class: 'e5-eje' }); t.textContent = auto(v); s.appendChild(t);
        }
        if (opc.base !== undefined) s.appendChild(svg('line', { x1: L, x2: W - R, y1: Y(opc.base), y2: Y(opc.base), stroke: 'rgba(255,255,255,.35)', 'stroke-dasharray': '4 4' }));
        var paso = Math.ceil(cats.length / 12);
        cats.forEach(function (c, i) {
            if (i % paso && i !== cats.length - 1) return;
            var t = svg('text', { x: X(i), y: H - B + 18, 'text-anchor': 'middle', class: 'e5-eje' }); t.textContent = c.etiqueta; s.appendChild(t);
        });
        var ty = svg('text', { x: 4, y: 10, class: 'e5-eje' }); ty.textContent = unidad || ''; s.appendChild(ty);
        series.forEach(function (se) {
            var d = '', ini = true;
            cats.forEach(function (c, i) {
                var v = se.valores[c.clave];
                if (v === null || v === undefined) { ini = true; return; }
                d += (ini ? 'M' : 'L') + X(i) + ' ' + Y(v) + ' '; ini = false;
            });
            s.appendChild(svg('path', { d: d, fill: 'none', stroke: se.color, 'stroke-width': se.grueso || 2.2 }));
            cats.forEach(function (c, i) {
                var v = se.valores[c.clave];
                if (v === null || v === undefined) return;
                var p = svg('circle', { cx: X(i), cy: Y(v), r: opc.clic ? 5.5 : 3.6, fill: se.color, class: 'e5-punto' + (opc.clic ? ' drill' : '') });
                conTip(p, se.nombre + ' · ' + c.etiqueta + ': ' + (opc.fmt ? opc.fmt(v) : auto(v)) + ' ' + (unidad || '') +
                    (opc.clic ? ' · clic para hacer drill-down' : ''), opc.clic ? function () { opc.clic(c.clave); } : null);
                s.appendChild(p);
            });
        });
        caja.appendChild(s);
    }
    // Barras horizontales: items [{etiqueta, valor, texto, color, foco, accion}]
    function barras(caja, items, opc) {
        opc = opc || {};
        if (!items.length) { caja.appendChild(crear('p', 'pob-mini', 'Sin datos para esta seleccion.')); return; }
        var neg = items.some(function (x) { return x.valor < 0; });
        var mx = Math.max.apply(null, items.map(function (x) { return Math.abs(x.valor) || 0; })) || 1;
        var cont = crear('div', 'pob-barras');
        items.forEach(function (x) {
            var f = crear('div', 'barra-h-fila' + (x.foco ? ' warm' : '') + (x.resto ? ' e5-resto' : ''));
            f.appendChild(crear('div', 'barra-h-label', x.etiqueta));
            var tr = crear('div', 'barra-h-track e5-track' + (neg ? ' div' : ''));
            var fi = crear('div', 'barra-h-fill');
            var w = Math.max(0.6, Math.abs(x.valor) / mx * (neg ? 50 : 100));
            fi.style.width = w + '%';
            if (neg) { fi.style.position = 'relative'; fi.style.left = x.valor < 0 ? (50 - w) + '%' : '50%'; }
            if (x.color) fi.style.background = x.color;
            else if (neg && x.valor < 0) fi.style.background = C_FRIO;
            else if (neg) fi.style.background = C_CALIDO;
            tr.appendChild(fi); f.appendChild(tr);
            f.appendChild(crear('div', 'barra-h-val pob-val', x.texto));
            conTip(f, x.etiqueta + ': ' + x.texto + (x.accion ? ' · clic para hacer drill-down' : ''), x.accion);
            if (x.accion) f.classList.add('e5-drill');
            cont.appendChild(f);
        });
        caja.appendChild(cont);
    }
    // Barras apiladas: items [{etiqueta, partes:[{v, color, nombre}], texto}]
    function apiladas(caja, items) {
        if (!items.length) { caja.appendChild(crear('p', 'pob-mini', 'Sin datos para esta seleccion.')); return; }
        var mx = Math.max.apply(null, items.map(function (x) { return x.partes.reduce(function (s, p) { return s + p.v; }, 0); })) || 1;
        var cont = crear('div', 'pob-barras');
        items.forEach(function (x) {
            var f = crear('div', 'barra-h-fila');
            f.appendChild(crear('div', 'barra-h-label', x.etiqueta));
            var tr = crear('div', 'barra-h-track'); tr.style.display = 'flex';
            x.partes.forEach(function (p) {
                var fi = crear('div', 'barra-h-fill'); fi.style.width = (p.v / mx * 100) + '%'; fi.style.background = p.color;
                fi.style.borderRadius = '0'; tr.appendChild(fi);
            });
            f.appendChild(tr);
            f.appendChild(crear('div', 'barra-h-val pob-val', x.texto));
            conTip(f, x.etiqueta + ': ' + x.partes.map(function (p) { return p.nombre + ' ' + dec(p.v, 0); }).join(' · '));
            cont.appendChild(f);
        });
        caja.appendChild(cont);
    }

    // ---- Matriz -----------------------------------------------------------------
    // opc: {filas:[{clave,etiqueta}], cols:[...], valor(f,c), totalF(f), totalC(c), total, fmt, div, clicFila, focoFila, etqF, etqC}
    function matriz(opc) {
        var t = el('mx'); vaciar(t);
        var vals = [];
        opc.filas.forEach(function (f) { opc.cols.forEach(function (c) { var v = opc.valor(f.clave, c.clave); if (v !== null && !isNaN(v)) vals.push(v); }); });
        var mx = Math.max.apply(null, vals.map(Math.abs).concat([0])) || 1;
        var mn = Math.min.apply(null, vals.concat([0]));
        var th = crear('thead'), tr = crear('tr');
        tr.appendChild(crear('th', '', opc.etqF + ' \\ ' + opc.etqC));
        opc.cols.forEach(function (c) { tr.appendChild(crear('th', '', c.etiqueta)); });
        if (opc.totalF) tr.appendChild(crear('th', 'e5-total', 'Total'));
        th.appendChild(tr); t.appendChild(th);
        var tb = crear('tbody');
        opc.filas.forEach(function (f) {
            var r = crear('tr');
            if (opc.focoFila && opc.focoFila(f.clave)) r.className = 'e5-foco-fila';
            var h = crear('th', opc.clicFila ? 'e5-clic' : '', f.etiqueta);
            if (opc.clicFila) conTip(h, f.etiqueta + ' · clic para hacer drill-down', function () { opc.clicFila(f.clave); });
            r.appendChild(h);
            opc.cols.forEach(function (c) {
                var v = opc.valor(f.clave, c.clave);
                var td = crear('td', 'mono', v === null || isNaN(v) ? '—' : opc.fmt(v));
                if (v !== null && !isNaN(v)) {
                    if (opc.div) td.style.background = v >= 0 ? 'rgba(255,106,77,' + (0.08 + Math.abs(v) / mx * 0.6) + ')' : 'rgba(73,199,224,' + (0.08 + Math.abs(v) / mx * 0.6) + ')';
                    else td.style.background = 'rgba(73,199,224,' + (0.05 + (mn >= 0 ? Math.sqrt(Math.abs(v) / mx) : Math.abs(v) / mx) * 0.55) + ')';
                    td.title = f.etiqueta + ' × ' + c.etiqueta + ': ' + opc.fmt(v);
                }
                r.appendChild(td);
            });
            if (opc.totalF) r.appendChild(crear('td', 'mono e5-total', opc.fmt(opc.totalF(f.clave))));
            tb.appendChild(r);
        });
        t.appendChild(tb);
        if (opc.totalC) {
            var tf = crear('tfoot'), r2 = crear('tr');
            r2.appendChild(crear('th', '', 'Total'));
            opc.cols.forEach(function (c) { r2.appendChild(crear('td', 'mono', opc.fmt(opc.totalC(c.clave)))); });
            if (opc.totalF) r2.appendChild(crear('td', 'mono e5-total', opc.fmt(opc.total)));
            tf.appendChild(r2); t.appendChild(tf);
        }
    }
    function cabMatriz(titulo, sub, nota) {
        el('mx-tit').textContent = titulo; el('mx-sub').textContent = sub || ''; el('mx-nota').textContent = nota || '';
    }
    function alPivot(fn) { el('mx-pivot').addEventListener('click', fn); }
    function interpretar(texto) { el('e5-interp').textContent = texto; }

    var NIV_T = { anio: 'Anio', semestre: 'Semestre', trimestre: 'Trimestre', mes: 'Mes' };
    var UNI = CFG.unidades || {};
    function un(i) { return (UNI[i] || '').replace('grados C (vs. base)', '°C').replace('grados C', '°C'); }

    // =========================================================================
    // VISTA 1 - Tiempo x Fuente x Indicador
    // =========================================================================
    function vista1() {
        var E = { ind: CFG.mensuales.indexOf('Anomalia de temperatura global') >= 0 ? 'Anomalia de temperatura global' : CFG.mensuales[0],
                  prov: ['NASA', 'NOAA'], nivel: 'anio', foco: null, pivot: false };
        var F = el('e5-filtros'), O = el('e5-operaciones');
        selector(F, 'Indicador (slice · dimension Indicador)', CFG.mensuales.map(function (i) { return [i, i + ' (' + UNI[i] + ')']; }),
            E.ind, function (v) { E.ind = v; correr(); }, '380px');
        casillas(F, 'Proveedor (slice o dice · dimension Fuente)', [['NASA', 'NASA'], ['NOAA', 'NOAA']], E.prov, function (v) { E.prov = v; correr(); });
        var selAnio = selector(F, 'Anio (slice · dimension Tiempo)', [['', 'Todos los anios']].concat(CFG.anios.map(function (a) { return [String(a), String(a)]; })),
            '', function (v) { E.foco = v ? parseInt(v, 10) : null; if (E.foco && E.nivel === 'anio') E.nivel = 'mes'; correr(); }, '200px');
        var seg = segmentos(O, 'Nivel de la jerarquia Tiempo (drill-down ↓ / roll-up ↑)',
            [['anio', 'Anio'], ['semestre', 'Semestre'], ['trimestre', 'Trimestre'], ['mes', 'Mes']], E.nivel,
            function (v) { E.nivel = v; correr(); });
        boton(O, '↑ Roll-up a Anio', function () { E.nivel = 'anio'; E.foco = null; selAnio.value = ''; correr(); });
        alPivot(function () { E.pivot = !E.pivot; correr(); });

        function filtros(conFoco) {
            var f = { indicador: [E.ind], proveedor: E.prov.slice() };
            if (conFoco && E.foco) f.anio = [E.foco];
            return f;
        }
        function correr() {
            seg.marcar(E.nivel);
            selAnio.value = E.foco ? String(E.foco) : '';
            if (!E.prov.length) { estado('Marca al menos un proveedor.'); return; }
            var u = un(E.ind);
            var colsMx = 'mes_del_anio';
            ciclo(function () {
                return Promise.all([
                    api('Visualizacion 1 · ' + NIV_T[E.nivel] + ' × proveedor', E.nivel, 'proveedor', 'valor', filtros(true)),
                    api('Visualizacion 2 · mes del anio', 'mes_del_anio', 'proveedor', 'valor', filtros(true)),
                    api('Matriz · anio × ' + (colsMx === 'mes_del_anio' ? 'mes' : colsMx), 'anio', colsMx === 'mes_del_anio' ? 'mes_del_anio' : null, 'valor', filtros(true)),
                    api('Indicador · registros', E.nivel, null, 'n', filtros(true))
                ]).then(function (R) {
                    var r1 = R[0], r2 = R[1], r3 = R[2], r4 = R[3];
                    // Seleccion activa
                    var chips = [{ op: 'slice', etq: 'Slice', texto: 'Indicador = ' + E.ind },
                                 { op: E.prov.length > 1 ? 'dice' : 'slice', etq: E.prov.length > 1 ? 'Dice' : 'Slice', texto: 'Proveedor = ' + E.prov.join(', ') }];
                    if (E.foco) chips.push({ op: 'slice', etq: 'Slice', texto: 'Anio = ' + E.foco });
                    chips.push({ op: E.nivel === 'anio' ? 'roll' : 'drill', etq: E.nivel === 'anio' ? 'Roll-up' : 'Drill-down', texto: 'Tiempo al nivel ' + NIV_T[E.nivel] });
                    if (E.pivot) chips.push({ op: 'pivot', etq: 'Pivot', texto: 'Matriz rotada' });
                    seleccion(chips);

                    // KPIs
                    var mejor = null;
                    r1.filas.forEach(function (f) { var v = totalFila(r1, f.clave); if (v !== null && (!mejor || v > mejor.v)) mejor = { f: f, v: v }; });
                    kpi(1, mejor ? auto(mejor.v) + ' ' + u : '—', 'valor mas alto en el nivel ' + NIV_T[E.nivel].toLowerCase(),
                        mejor ? mejor.f.etiqueta + ' (promedio de los proveedores elegidos)' : '');
                    var fs = r1.filas, ini = fs.length ? totalFila(r1, fs[0].clave) : null, fin = fs.length ? totalFila(r1, fs[fs.length - 1].clave) : null;
                    kpi(2, ini !== null && fin !== null ? signo(fin - ini, 2, ' ' + u) : '—', 'cambio entre el primer y el ultimo periodo',
                        fs.length ? fs[0].etiqueta + ' → ' + fs[fs.length - 1].etiqueta : '');
                    var provs = r1.columnas.map(function (c) { return c.clave; });
                    if (provs.length >= 2) {
                        var difs = [];
                        fs.forEach(function (f) { var a = celda(r1, f.clave, provs[0]), b = celda(r1, f.clave, provs[1]); if (a !== null && b !== null) difs.push(a - b); });
                        var md = difs.reduce(function (s, x) { return s + x; }, 0) / (difs.length || 1);
                        kpi(3, signo(md, 2, ' ' + u), 'brecha media ' + provs[0] + ' − ' + provs[1], difs.length + ' periodos con ambas fuentes');
                    } else {
                        kpi(3, dec(r4.n_hechos, 0), 'registros mensuales en la seleccion', 'una sola fuente: ' + (provs[0] || '—'));
                    }

                    // Visualizacion 1: serie por proveedor en el nivel elegido
                    var g1 = grafica(1, E.ind + ' por ' + NIV_T[E.nivel].toLowerCase(),
                        'AVG(valor) de los meses de cada periodo, recalculado en SQL al cambiar de nivel (' + u + ').');
                    var series = r1.columnas.map(function (c, k) {
                        var vs = {}; r1.filas.forEach(function (f) { vs[f.clave] = celda(r1, f.clave, c.clave); });
                        return { nombre: c.etiqueta, color: PALETA[k], valores: vs };
                    });
                    leyenda(g1.ley, series);
                    lineas(g1.cuerpo, r1.filas, series, u, {
                        clic: E.nivel === 'anio' ? function (anio) { E.foco = anio; E.nivel = 'mes'; correr(); } : null,
                        fmt: function (v) { return dec(v, 2); }
                    });

                    // Visualizacion 2: perfil estacional (mes del anio)
                    var g2 = grafica(2, 'Perfil por mes del anio', 'Promedio de cada mes calendario en los anios filtrados: muestra la estacionalidad que el promedio anual esconde.');
                    var prom = r2.filas.map(function (f) { return { etiqueta: f.etiqueta, valor: totalFila(r2, f.clave) }; });
                    var vmin = Math.min.apply(null, prom.map(function (x) { return x.valor; }));
                    barras(g2.cuerpo, prom.map(function (x) {
                        return { etiqueta: x.etiqueta, valor: x.valor - vmin + (E.ind.indexOf('Anomalia') === 0 ? 0.0001 : 0.05),
                                 texto: dec(x.valor, 2) + ' ' + u };
                    }));
                    g2.ley.appendChild(crear('span', 'pob-mini', 'La barra mide la distancia al mes mas bajo (' + dec(vmin, 2) + ' ' + u + ').'));

                    // Matriz: anio x mes (o pivot)
                    var colsR = r3.columnas.length ? r3.columnas : [{ clave: null, etiqueta: E.ind }];
                    var pf = E.pivot ? colsR : r3.filas, pc = E.pivot ? r3.filas : colsR;
                    cabMatriz('Anio × ' + (r3.columnas.length ? 'mes del anio' : 'valor'),
                        'AVG(valor) en ' + u + ' de los proveedores elegidos. Totales calculados con su propia consulta (promedio de todos los meses, no promedio de promedios).',
                        'Pivot: ' + (E.pivot ? 'meses en filas, anios en columnas.' : 'anios en filas, meses en columnas.'));
                    matriz({
                        filas: pf, cols: pc, etqF: E.pivot ? 'Mes' : 'Anio', etqC: E.pivot ? 'Anio' : 'Mes',
                        valor: function (f, c) { return E.pivot ? celda(r3, c, f) : celda(r3, f, c); },
                        totalF: function (f) { return E.pivot ? totalCol(r3, f) : totalFila(r3, f); },
                        totalC: function (c) { return E.pivot ? totalFila(r3, c) : totalCol(r3, c); },
                        total: r3.total, fmt: function (v) { return v === null ? '—' : dec(v, 2); },
                        clicFila: E.pivot ? null : function (a) { E.foco = a; E.nivel = 'mes'; correr(); }
                    });

                    // Interpretacion
                    var txt = 'Con ' + dec(r4.n_hechos, 0) + ' registros mensuales de ' + E.prov.join(' y ') + (E.foco ? ' en ' + E.foco : '') +
                        ', al nivel ' + NIV_T[E.nivel].toLowerCase() + ' el valor mas alto de ' + E.ind.toLowerCase() + ' es ' +
                        (mejor ? mejor.f.etiqueta + ' (' + dec(mejor.v, 2) + ' ' + u + ')' : '—') + '. ';
                    if (prom.length) {
                        var pmx = prom.reduce(function (a, b) { return b.valor > a.valor ? b : a; }), pmn = prom.reduce(function (a, b) { return b.valor < a.valor ? b : a; });
                        txt += 'En el perfil mensual, ' + pmx.etiqueta + ' es el mes mas alto y ' + pmn.etiqueta + ' el mas bajo (diferencia de ' + dec(pmx.valor - pmn.valor, 2) + ' ' + u + '). ';
                    }
                    txt += E.nivel === 'anio' ? 'Haz drill-down a Mes para ver los episodios que el promedio anual suaviza.' :
                        'Haz roll-up a Anio para volver a la tendencia.';
                    interpretar(txt);
                });
            });
        }
        correr();
    }

    // =========================================================================
    // VISTA 2 - Geografia (Mundo > Region > Pais) x Indicador x Tiempo
    // =========================================================================
    function vista2() {
        var refAnio = CFG.anios.indexOf(2024) >= 0 ? 2024 : CFG.anios[CFG.anios.length - 1];
        var E = { ind: 'Emisiones de CO2 (total)', anio: refAnio, region: null, pivot: false };
        var F = el('e5-filtros'), O = el('e5-operaciones');
        selector(F, 'Indicador (slice · dimension Indicador)', CFG.territoriales.map(function (i) { return [i, i + ' (' + UNI[i] + ')']; }),
            E.ind, function (v) { E.ind = v; correr(); }, '380px');
        selector(F, 'Anio (slice · dimension Tiempo)', CFG.anios.filter(function (a) { return a <= refAnio; }).map(function (a) { return [String(a), String(a)]; }),
            String(E.anio), function (v) { E.anio = parseInt(v, 10); correr(); }, '200px');
        var selReg = selector(O, 'Drill-down a una region (Geografia: Region → Pais)', [['', 'Nivel Region (todas)']].concat(CFG.regiones.map(function (r) { return [r, r]; })),
            '', function (v) { E.region = v || null; correr(); }, '300px');
        boton(O, '↑ Roll-up a Region', function () { E.region = null; correr(); });
        alPivot(function () { E.pivot = !E.pivot; correr(); });

        function correr() {
            selReg.value = E.region || '';
            var u = un(E.ind);
            var nivel = E.region ? 'pais' : 'region';
            var f = { indicador: [E.ind], nivel: ['Nacional'] };
            if (E.region) f.region = [E.region];
            var fA = JSON.parse(JSON.stringify(f)); fA.anio = [E.anio];
            ciclo(function () {
                return Promise.all([
                    api('Visualizacion 1 · ' + nivel + ' en ' + E.anio, nivel, null, 'valor', fA),
                    api('Indicador · paises con dato', nivel, null, 'paises', fA),
                    api('Visualizacion 2 y matriz · ' + nivel + ' × anio', nivel, 'anio', 'valor', f)
                ]).then(function (R) {
                    var r1 = R[0], rp = R[1], r3 = R[2];
                    seleccion([{ op: 'slice', etq: 'Slice', texto: 'Indicador = ' + E.ind },
                               { op: 'slice', etq: 'Slice', texto: 'Anio = ' + E.anio + ' (barras e indicadores)' },
                               { op: 'slice', etq: 'Slice', texto: 'Nivel = Nacional (se suman paises)' },
                               E.region ? { op: 'drill', etq: 'Drill-down', texto: 'Region = ' + E.region + ' → paises' } : { op: 'roll', etq: 'Roll-up', texto: 'Paises → Region' }]
                        .concat(E.pivot ? [{ op: 'pivot', etq: 'Pivot', texto: 'Matriz rotada' }] : []));
                    var tot = r1.total || 0;
                    var items = r1.filas.map(function (x) { return { clave: x.clave, etiqueta: x.etiqueta, v: totalFila(r1, x.clave) || 0 }; })
                        .filter(function (x) { return x.v > 0; }).sort(function (a, b) { return b.v - a.v; });
                    // KPIs
                    kpi(1, auto(tot) + ' ' + u, 'total ' + (E.region ? 'de ' + E.region : 'mundial (suma de paises)') + ' en ' + E.anio,
                        dec(rp.total, 0) + ' paises con dato (COUNT DISTINCT)');
                    kpi(2, items.length ? pct(items[0].v / tot * 100) : '—', 'participacion del primer ' + (E.region ? 'pais' : 'continente'), items.length ? items[0].etiqueta : '');
                    var posCol = items.map(function (x) { return x.clave; }).indexOf('Colombia');
                    if (posCol >= 0) kpi(3, '#' + (posCol + 1) + ' de ' + items.length, 'posicion de Colombia', pct(items[posCol].v / tot * 100) + ' del total de la region');
                    else {
                        var ac = 0, n50 = 0; for (var i = 0; i < items.length; i++) { ac += items[i].v; n50 = i + 1; if (ac >= tot / 2) break; }
                        kpi(3, String(n50), (E.region ? 'paises' : 'continentes') + ' reunen la mitad del total', 'de ' + items.length + ' con dato');
                    }
                    // Visualizacion 1: barras del nivel (drill-down al hacer clic en una region)
                    var g1 = grafica(1, E.ind + ' por ' + (E.region ? 'pais de ' + E.region : 'region') + ', ' + E.anio,
                        'SUM(valor) en ' + u + ' y participacion % dentro del nivel.' + (E.region ? '' : ' Clic en una region para bajar a sus paises.'));
                    var MAX = 12, lista = items.slice(0, MAX);
                    if (posCol >= MAX) lista.push(items[posCol]);
                    var vis = lista.map(function (x) {
                        return { etiqueta: x.etiqueta, valor: x.v, texto: auto(x.v) + ' · ' + pct(x.v / tot * 100), foco: x.clave === 'Colombia',
                                 accion: E.region ? null : function () { E.region = x.clave; correr(); } };
                    });
                    if (items.length > lista.length) {
                        var rv = items.filter(function (x) { return lista.indexOf(x) < 0; }).reduce(function (s, x) { return s + x.v; }, 0);
                        vis.push({ etiqueta: 'Resto (' + (items.length - lista.length) + ')', valor: rv, texto: auto(rv) + ' · ' + pct(rv / tot * 100), resto: true });
                    }
                    barras(g1.cuerpo, vis);
                    // Visualizacion 2: participacion por anio (recalculada contra el total de cada anio)
                    var anios = r3.columnas;
                    var top = items.slice(0, 4).map(function (x) { return x.clave; });
                    if (posCol >= 4) top.push('Colombia');
                    var g2 = grafica(2, 'Participacion % por anio · ' + (E.region || 'regiones'),
                        'Cada punto = valor del miembro / total del nivel en ese anio × 100 (ambos consultados al modelo).');
                    var series = top.map(function (k, i) {
                        var vs = {}; anios.forEach(function (a) { var v = celda(r3, k, a.clave), t = totalCol(r3, a.clave); vs[a.clave] = v !== null && t ? v / t * 100 : null; });
                        var etq = (r3.filas.filter(function (f) { return f.clave === k; })[0] || {}).etiqueta || k;
                        return { nombre: etq, color: k === 'Colombia' ? C_CALIDO : PALETA[i % PALETA.length], valores: vs, grueso: k === 'Colombia' ? 3 : 2 };
                    });
                    leyenda(g2.ley, series);
                    lineas(g2.cuerpo, anios, series, '%', { fmt: function (v) { return pct(v); } });
                    // Matriz: miembro x anio
                    var orden = items.map(function (x) { return x.clave; });
                    var filasMx = r3.filas.slice().sort(function (a, b) { return orden.indexOf(a.clave) - orden.indexOf(b.clave); })
                        .filter(function (f) { return orden.indexOf(f.clave) >= 0 && (orden.indexOf(f.clave) < 15 || f.clave === 'Colombia'); });
                    var pf = E.pivot ? anios : filasMx, pc = E.pivot ? filasMx : anios;
                    cabMatriz((E.region ? 'Paises de ' + E.region : 'Regiones') + ' × anio',
                        'SUM(valor) en ' + u + '. El total de cada anio sale de su propia consulta; no se suman anios entre si.',
                        (filasMx.length < r3.filas.length ? 'Se muestran los 15 miembros con mas valor en ' + E.anio + (posCol >= 15 ? ' y Colombia' : '') + '; los totales incluyen a todos. ' : '') +
                        'Clic en una region para drill-down. Pivot: ' + (E.pivot ? 'anios en filas.' : 'territorios en filas.'));
                    matriz({
                        filas: pf, cols: pc, etqF: E.pivot ? 'Anio' : (E.region ? 'Pais' : 'Region'), etqC: E.pivot ? (E.region ? 'Pais' : 'Region') : 'Anio',
                        valor: function (f, c) { return E.pivot ? celda(r3, c, f) : celda(r3, f, c); },
                        // Solo se totaliza entre territorios: sumar anios no tiene sentido para
                        // stocks como la poblacion, asi que el total sobre el tiempo se omite.
                        totalF: E.pivot ? function (f) { return totalCol(r3, f); } : null,
                        totalC: E.pivot ? null : function (c) { return totalCol(r3, c); },
                        total: r3.total, fmt: auto,
                        focoFila: function (k) { return k === 'Colombia'; },
                        clicFila: !E.pivot && !E.region ? function (k) { E.region = k; correr(); } : null
                    });
                    // Interpretacion
                    var t = E.region
                        ? 'En ' + E.region + ', ' + (items[0] ? items[0].etiqueta + ' aporta ' + pct(items[0].v / tot * 100) : '') + ' de ' + E.ind.toLowerCase() + ' en ' + E.anio + '. '
                        : (items[0] ? items[0].etiqueta + ' concentra ' + pct(items[0].v / tot * 100) + ' del total mundial de ' + E.ind.toLowerCase() + ' en ' + E.anio + '. ' : '');
                    if (posCol >= 0) t += 'Colombia ocupa el puesto ' + (posCol + 1) + ' de ' + items.length + ' con ' + pct(items[posCol].v / tot * 100) + '. ';
                    if (series.length && anios.length > 1) {
                        var s0 = series[0], a0 = anios[0].clave, a1 = anios[anios.length - 1].clave;
                        if (s0.valores[a0] !== null && s0.valores[a1] !== null)
                            t += 'La participacion de ' + s0.nombre + ' pasa de ' + pct(s0.valores[a0]) + ' a ' + pct(s0.valores[a1]) + ' entre ' + anios[0].etiqueta + ' y ' + anios[anios.length - 1].etiqueta + '. ';
                    }
                    t += E.region ? 'Usa «Roll-up a Region» para volver a la comparacion entre continentes.' : 'Haz drill-down en Sudamerica para ubicar a Colombia frente a sus pares.';
                    interpretar(t);
                });
            });
        }
        correr();
    }

    // =========================================================================
    // VISTA 3 - Territorio x Tiempo x Indicador (slice y dice)
    // =========================================================================
    function vista3() {
        var anios = CFG.anios.filter(function (a) { return a <= 2024; });
        var E = { ind: 'Emisiones de CO2 (total)', medida: 'var', ter: CFG.territorios.map(function (t) { return t.clave; }),
                  anios: anios.map(String), region: null, pivot: false };
        var etqTer = {}; CFG.territorios.forEach(function (t) { etqTer[t.clave] = t.etiqueta; });
        var F = el('e5-filtros'), O = el('e5-operaciones');
        selector(F, 'Indicador (slice · dimension Indicador)', CFG.mapa.map(function (i) { return [i, i + ' (' + UNI[i] + ')']; }),
            E.ind, function (v) { E.ind = v; correr(); }, '380px');
        var cajaTer = casillas(F, 'Territorios (dice · dimension Geografia)', CFG.territorios.map(function (t) { return [t.clave, t.etiqueta]; }), E.ter,
            function (v) { E.ter = v; correr(); });
        casillas(F, 'Anios (dice · dimension Tiempo)', anios.map(function (a) { return [String(a), String(a)]; }), E.anios, function (v) { E.anios = v; correr(); });
        selector(O, 'Medida', [['var', 'Variacion frente al primer anio elegido'], ['valor', 'Valor del indicador'], ['indice', 'Indice: mundo = 100']],
            E.medida, function (v) { E.medida = v; correr(); }, '320px');
        var selReg = selector(O, 'Drill-down: paises de una region', [['', 'Sin drill-down (regiones)']].concat(CFG.regiones.map(function (r) { return [r, r]; })),
            '', function (v) { E.region = v || null; correr(); }, '280px');
        boton(O, '↑ Roll-up a regiones', function () { E.region = null; correr(); });
        alPivot(function () { E.pivot = !E.pivot; correr(); });

        function correr() {
            selReg.value = E.region || '';
            cajaTer.parentNode.style.opacity = E.region ? '.45' : '1';
            if (!E.anios.length || (!E.region && !E.ter.length)) { estado('Marca al menos un territorio y un anio para formar el subcubo (dice).'); return; }
            var u = un(E.ind), esPct = u === '%';
            var aniosSel = E.anios.map(Number).sort();
            var f = { indicador: [E.ind], anio: aniosSel };
            if (E.region) { f.region = [E.region]; f.nivel = ['Nacional']; } else f.pais = E.ter.slice();
            var fM = { indicador: [E.ind], anio: aniosSel, pais: ['World'] };
            ciclo(function () {
                return Promise.all([
                    api('Matriz y visualizaciones · territorio × anio', 'territorio', 'anio', 'valor', f),
                    api('Referencia · Mundo por anio', 'anio', null, 'valor', fM)
                ]).then(function (R) {
                    var r = R[0], rw = R[1];
                    var cols = r.columnas, a0 = cols.length ? cols[0].clave : null, aN = cols.length ? cols[cols.length - 1].clave : null;
                    var filas = r.filas.slice();
                    if (E.region) { // drill-down: los 10 paises con mas valor en el ultimo anio, y Colombia
                        filas.sort(function (x, y) { return (celda(r, y.clave, aN) || 0) - (celda(r, x.clave, aN) || 0); });
                        filas = filas.filter(function (x, i) { return i < 10 || x.clave === 'Colombia'; });
                    } else {
                        var orden = CFG.territorios.map(function (t) { return t.clave; });
                        filas.sort(function (x, y) { return orden.indexOf(x.clave) - orden.indexOf(y.clave); });
                    }
                    function mundo(a) { return celda(rw, a); }
                    function med(k, a) {
                        var v = celda(r, k, a); if (v === null) return null;
                        if (E.medida === 'valor') return v;
                        if (E.medida === 'var') { var b = celda(r, k, a0); if (b === null) return null; return esPct ? v - b : (b ? (v / b - 1) * 100 : null); }
                        var w = mundo(a); return w ? v / w * 100 : null;
                    }
                    function fmt(v) {
                        if (v === null) return '—';
                        if (E.medida === 'valor') return auto(v);
                        if (E.medida === 'var') return esPct ? signo(v, 1, ' pp') : signo(v);
                        return dec(v, 0);
                    }
                    var sufMed = E.medida === 'valor' ? u : E.medida === 'var' ? (esPct ? 'pp' : '%') : 'mundo = 100';
                    seleccion([{ op: 'slice', etq: 'Slice', texto: 'Indicador = ' + E.ind },
                               E.region ? { op: 'drill', etq: 'Drill-down', texto: 'Region = ' + E.region + ' → paises' }
                                        : { op: 'dice', etq: 'Dice', texto: 'Territorios = ' + E.ter.map(function (k) { return etqTer[k]; }).join(', ') },
                               { op: 'dice', etq: 'Dice', texto: 'Anios = ' + aniosSel.join(', ') }]
                        .concat(E.pivot ? [{ op: 'pivot', etq: 'Pivot', texto: 'Matriz rotada' }] : []));

                    // Cambio total primer -> ultimo anio elegido
                    var cambios = filas.map(function (x) {
                        var b = celda(r, x.clave, a0), v = celda(r, x.clave, aN);
                        return { clave: x.clave, etiqueta: x.etiqueta, c: b !== null && v !== null ? (esPct ? v - b : (b ? (v / b - 1) * 100 : null)) : null, v: v };
                    }).filter(function (x) { return x.c !== null; });
                    var orden2 = cambios.slice().sort(function (a, b) { return b.c - a.c; });
                    var suf = esPct ? ' pp' : '%';
                    kpi(1, orden2.length ? signo(orden2[0].c, 1, suf) : '—', 'mayor aumento ' + a0 + '–' + aN, orden2.length ? orden2[0].etiqueta : '');
                    var ult = orden2[orden2.length - 1];
                    kpi(2, ult ? signo(ult.c, 1, suf) : '—', ult && ult.c < 0 ? 'mayor reduccion ' + a0 + '–' + aN : 'menor aumento ' + a0 + '–' + aN, ult ? ult.etiqueta : '');
                    var col = celda(r, 'Colombia', aN), w = mundo(aN);
                    kpi(3, col !== null && w ? dec(col / w * 100, col / w * 100 < 10 ? 2 : 0) : '—', 'Colombia frente al mundo en ' + aN + ' (mundo = 100)',
                        col !== null ? auto(col) + ' ' + u + ' frente a ' + auto(w) + ' ' + u : 'Colombia no esta en el subcubo');

                    // Visualizacion 1: trayectorias segun la medida elegida
                    var g1 = grafica(1, 'Trayectoria por territorio · ' + sufMed,
                        E.medida === 'var' ? 'Cambio acumulado frente a ' + a0 + ' (linea punteada = sin cambio).' :
                        E.medida === 'indice' ? 'Cada territorio comparado con el mundo del mismo anio (linea punteada = mundo).' : 'Valor publicado por la fuente (' + u + ').');
                    var series = filas.slice(0, 9).map(function (x, i) {
                        var vs = {}; cols.forEach(function (c) { vs[c.clave] = med(x.clave, c.clave); });
                        return { nombre: x.etiqueta, color: x.clave === 'Colombia' ? C_CALIDO : x.clave === 'World' ? '#ffffff' : PALETA[i % PALETA.length], valores: vs, grueso: x.clave === 'Colombia' ? 3 : 2 };
                    });
                    leyenda(g1.ley, series);
                    lineas(g1.cuerpo, cols, series, sufMed, { base: E.medida === 'var' ? 0 : E.medida === 'indice' ? 100 : undefined, fmt: fmt });

                    // Visualizacion 2: cambio total (barras divergentes)
                    var g2 = grafica(2, 'Cambio total ' + a0 + ' → ' + aN, (esPct ? 'Puntos porcentuales' : 'Variacion %') + '; rojo = aumento, azul = reduccion.');
                    barras(g2.cuerpo, orden2.map(function (x) { return { etiqueta: x.etiqueta, valor: x.c, texto: signo(x.c, 1, suf), foco: x.clave === 'Colombia' }; }));

                    // Matriz
                    var pf = E.pivot ? cols : filas, pc = E.pivot ? filas : cols;
                    cabMatriz((E.region ? 'Paises de ' + E.region : 'Territorios') + ' × anio · ' + sufMed,
                        'Celdas consultadas al modelo con el slice y el dice activos; la medida se calcula sobre ellas.',
                        'Pivot: ' + (E.pivot ? 'anios en filas.' : 'territorios en filas.') + (E.region ? ' Se muestran los 10 paises con mas valor en ' + aN + '.' : ''));
                    matriz({
                        filas: pf, cols: pc, etqF: E.pivot ? 'Anio' : 'Territorio', etqC: E.pivot ? 'Territorio' : 'Anio',
                        valor: function (a, b) { return E.pivot ? med(b, a) : med(a, b); }, fmt: fmt, div: E.medida === 'var',
                        focoFila: function (k) { return k === 'Colombia'; },
                        clicFila: !E.pivot && !E.region ? function (k) {
                            var reg = etqTer[k]; if (CFG.regiones.indexOf(reg) >= 0) { E.region = reg; correr(); }
                        } : null
                    });

                    // Interpretacion
                    var t = 'En el subcubo de ' + filas.length + ' territorios × ' + cols.length + ' anios, ';
                    if (orden2.length) t += orden2[0].etiqueta + ' es el que mas sube (' + signo(orden2[0].c, 1, suf) + ') y ' + ult.etiqueta + (ult.c < 0 ? ' el que mas baja (' : ' el que menos sube (') + signo(ult.c, 1, suf) + ') entre ' + a0 + ' y ' + aN + '. ';
                    var cc = cambios.filter(function (x) { return x.clave === 'Colombia'; })[0];
                    var cw = cambios.filter(function (x) { return x.clave === 'World'; })[0];
                    if (cc && cw) t += 'Colombia cambia ' + signo(cc.c, 1, suf) + ' frente a ' + signo(cw.c, 1, suf) + ' del mundo. ';
                    t += a0 === 2020 && !esPct ? 'Ojo: 2020 fue el anio de la pandemia; quita 2020 del dice para medir desde 2021.' : '';
                    interpretar(t);
                });
            });
        }
        correr();
    }

    // =========================================================================
    // VISTA 4 - Tabla dinamica: Geografia x Indicador x Fuente (calidad)
    // =========================================================================
    function vista4() {
        var A = CFG.atributos, J = CFG.jerarquias;
        var ATTRS = ['nivel', 'region', 'pais', 'categoria', 'indicador', 'tipo_fuente', 'proveedor', 'fuente', 'anio'];
        var E = { filas: 'nivel', cols: 'categoria', medida: 'pat', f: { tipo_fuente: [], anio: [], nivel: [] }, ruta: [] };
        var F = el('e5-filtros'), O = el('e5-operaciones');
        var selTipo = selector(F, 'Tipo de fuente (slice · dimension Fuente)', [['', 'Todos'], ['Primaria', 'Primaria'], ['Terciaria', 'Terciaria']], '',
            function (v) { E.f.tipo_fuente = v ? [v] : []; correr(); }, '220px');
        var selAnio = selector(F, 'Anio (slice · dimension Tiempo)', [['', 'Todos']].concat(CFG.anios.map(function (a) { return [String(a), String(a)]; })), '',
            function (v) { E.f.anio = v ? [parseInt(v, 10)] : []; correr(); }, '180px');
        var selNiv = selector(F, 'Nivel geografico (slice · dimension Geografia)', [['', 'Todos'], ['Nacional', 'Nacional'], ['Regional', 'Regional'], ['Global', 'Global']], '',
            function (v) { E.f.nivel = v ? [v] : []; correr(); }, '240px');
        var opsAttr = ATTRS.map(function (k) { return [k, A[k].dimension + ' · ' + A[k].nivel]; });
        var selF = selector(O, 'Filas', opsAttr, E.filas, function (v) { E.filas = v; E.ruta = []; correr(); }, '240px');
        var selC = selector(O, 'Columnas', [['', '(ninguna)']].concat(opsAttr), E.cols, function (v) { E.cols = v; correr(); }, '240px');
        selector(O, 'Medida', [['pat', '% de atipicos'], ['n', 'Numero de registros'], ['at', 'Registros atipicos'], ['z', 'Valor z promedio']],
            E.medida, function (v) { E.medida = v; correr(); }, '220px');
        var bDown = boton(O, '↓ Drill-down filas', function () { mover(1); }, 'Bajar un nivel en la jerarquia de la dimension de las filas');
        var bUp = boton(O, '↑ Roll-up filas', function () { mover(-1); }, 'Subir un nivel en la jerarquia de la dimension de las filas');
        boton(O, 'Quitar filtros', function () {
            E.f = { tipo_fuente: [], anio: [], nivel: [] }; E.ruta = []; selTipo.value = ''; selAnio.value = ''; selNiv.value = ''; correr();
        });
        alPivot(function () { if (!E.cols) return; var t = E.filas; E.filas = E.cols; E.cols = t; correr(); });

        function jer(attr) { var d = A[attr].dimension; return J[d] || []; }
        function mover(paso) {
            var h = jer(E.filas), i = h.indexOf(E.filas);
            if (i < 0 || !h[i + paso]) return;
            if (paso < 0 && E.ruta.length) { var u = E.ruta.pop(); E.f[u.attr] = []; if (u.attr === 'nivel') selNiv.value = ''; }
            E.filas = h[i + paso];
            if (E.cols === E.filas) E.cols = '';
            correr();
        }
        function drillMiembro(clave, etiqueta) {
            var h = jer(E.filas), i = h.indexOf(E.filas);
            if (i < 0 || !h[i + 1]) return;
            E.f[E.filas] = [clave]; E.ruta.push({ attr: E.filas, valor: etiqueta });
            if (E.filas === 'nivel') selNiv.value = clave;
            E.filas = h[i + 1];
            if (E.cols === E.filas) E.cols = '';
            correr();
        }
        function fmtM(v) {
            if (v === null || v === undefined) return '—';
            return E.medida === 'pat' ? pct(v) : E.medida === 'z' ? dec(v, 2) : dec(v, 0);
        }
        function correr() {
            selF.value = E.filas; selC.value = E.cols;
            var h = jer(E.filas), i = h.indexOf(E.filas);
            bDown.disabled = !(i >= 0 && h[i + 1]); bUp.disabled = !(i > 0);
            var f = {}; Object.keys(E.f).forEach(function (k) { if (E.f[k] && E.f[k].length) f[k] = E.f[k]; });
            ciclo(function () {
                return Promise.all([
                    api('Matriz · ' + E.filas + (E.cols ? ' × ' + E.cols : ''), E.filas, E.cols || null, E.medida, f),
                    api('Visualizacion 2 · registros', E.filas, null, 'n', f),
                    api('Visualizacion 2 · atipicos', E.filas, null, 'at', f),
                    api('Indicador · % de atipicos del subcubo', E.filas, null, 'pat', f)
                ]).then(function (R) {
                    var r = R[0], rn = R[1], ra = R[2], rp = R[3];
                    var chips = [];
                    Object.keys(f).forEach(function (k) {
                        if (!E.ruta.some(function (x) { return x.attr === k; }))
                            chips.push({ op: f[k].length > 1 ? 'dice' : 'slice', etq: f[k].length > 1 ? 'Dice' : 'Slice', texto: A[k].nivel + ' = ' + f[k].join(', ') });
                    });
                    E.ruta.forEach(function (x) { chips.push({ op: 'drill', etq: 'Drill-down', texto: A[x.attr].nivel + ' = ' + x.valor }); });
                    chips.push({ op: 'pivot', etq: 'Ejes', texto: 'Filas: ' + A[E.filas].nivel + (E.cols ? ' · Columnas: ' + A[E.cols].nivel : '') });
                    if (Object.keys(f).length >= 2 && !chips.some(function (c) { return c.op === 'dice'; })) chips.unshift({ op: 'dice', etq: 'Dice', texto: Object.keys(f).length + ' dimensiones filtradas' });
                    seleccion(chips);

                    // KPIs
                    kpi(1, pct(rp.total), '% de atipicos del subcubo', dec(ra.total || 0, 0) + ' de ' + dec(rn.total || 0, 0) + ' registros');
                    kpi(2, dec(rn.total || 0, 0), 'registros en el subcubo', r.filas.length + ' miembros de ' + A[E.filas].nivel.toLowerCase());
                    var mejor = null;
                    r.filas.forEach(function (fi) {
                        (r.columnas.length ? r.columnas : [{ clave: null, etiqueta: '' }]).forEach(function (c) {
                            var v = celda(r, fi.clave, c.clave), n = r.conteos[fi.clave + '|' + (c.clave === null ? '' : c.clave)] || 0;
                            if (v !== null && n >= 20 && (!mejor || v > mejor.v)) mejor = { v: v, t: fi.etiqueta + (c.etiqueta ? ' × ' + c.etiqueta : ''), n: n };
                        });
                    });
                    kpi(3, mejor ? fmtM(mejor.v) : '—', 'celda con el valor mas alto (≥ 20 registros)', mejor ? mejor.t + ' · ' + dec(mejor.n, 0) + ' registros' : '');

                    // Visualizacion 1: medida por miembro de las filas (drill-down al hacer clic)
                    var g1 = grafica(1, selMedida() + ' por ' + A[E.filas].nivel.toLowerCase(),
                        'Recalculado en SQL para cada miembro' + (E.medida === 'pat' ? ' con SUM(atipico) / SUM(n_registros)' : '') + '. Clic para hacer drill-down.');
                    var items = rp.filas.map(function (x) {
                        var v = E.medida === 'pat' ? totalFila(rp, x.clave) : E.medida === 'n' ? totalFila(rn, x.clave) : E.medida === 'at' ? totalFila(ra, x.clave) : totalFila(r, x.clave);
                        return { clave: x.clave, etiqueta: x.etiqueta, v: v };
                    }).sort(function (a, b) { return (b.v || 0) - (a.v || 0); }).slice(0, 15);
                    var puede = i >= 0 && h[i + 1];
                    barras(g1.cuerpo, items.map(function (x) {
                        return { etiqueta: x.etiqueta, valor: x.v || 0, texto: fmtM(x.v), accion: puede ? function () { drillMiembro(x.clave, x.etiqueta); } : null };
                    }));
                    // Visualizacion 2: composicion normales / atipicos
                    var g2 = grafica(2, 'Registros normales y atipicos por ' + A[E.filas].nivel.toLowerCase(), 'SUM(n_registros) − SUM(atipico) y SUM(atipico).');
                    leyenda(g2.ley, [{ nombre: 'Normales', color: C_FRIO }, { nombre: 'Atipicos', color: C_CALIDO }]);
                    apiladas(g2.cuerpo, rn.filas.map(function (x) {
                        var n = totalFila(rn, x.clave) || 0, a = totalFila(ra, x.clave) || 0;
                        return { etiqueta: x.etiqueta, n: n, partes: [{ v: n - a, color: C_FRIO, nombre: 'Normales' }, { v: a, color: C_CALIDO, nombre: 'Atipicos' }],
                                 texto: dec(n, 0) + ' · ' + pct(n ? a / n * 100 : 0) };
                    }).sort(function (a, b) { return b.n - a.n; }).slice(0, 15));

                    // Matriz
                    var cols = r.columnas.length ? r.columnas : [{ clave: null, etiqueta: selMedida() }];
                    cabMatriz(selMedida() + ': ' + A[E.filas].nivel + (E.cols ? ' × ' + A[E.cols].nivel : ''),
                        'Cada celda y cada total es una consulta GROUP BY al modelo; los porcentajes y promedios no se suman.',
                        'Pivot intercambia filas y columnas. Clic en el nombre de una fila para hacer drill-down en su jerarquia.');
                    matriz({
                        filas: r.filas, cols: cols, etqF: A[E.filas].nivel, etqC: E.cols ? A[E.cols].nivel : 'Medida',
                        valor: function (a, b) { return celda(r, a, b); },
                        totalF: E.cols ? function (a) { return totalFila(r, a); } : null,
                        totalC: function (b) { return E.cols ? totalCol(r, b) : r.total; }, total: r.total, fmt: fmtM,
                        clicFila: puede ? function (k) { var x = r.filas.filter(function (y) { return y.clave === k; })[0]; drillMiembro(k, x.etiqueta); } : null
                    });

                    // Interpretacion
                    var t = 'En el subcubo (' + dec(rn.total || 0, 0) + ' registros) el ' + pct(rp.total) + ' esta marcado como atipico. ';
                    if (items.length) t += 'Por ' + A[E.filas].nivel.toLowerCase() + ', el valor mas alto de ' + selMedida().toLowerCase() + ' es ' + items[0].etiqueta + ' (' + fmtM(items[0].v) + ')' +
                        (items.length > 1 ? ' y el mas bajo ' + items[items.length - 1].etiqueta + ' (' + fmtM(items[items.length - 1].v) + '). ' : '. ');
                    if (mejor) t += 'La combinacion mas alta es ' + mejor.t + '. ';
                    if (!E.f.nivel.length && E.filas !== 'nivel') t += 'Haz slice en Nivel = Nacional para quitar el efecto de los agregados regionales.';
                    interpretar(t);
                });
            });
        }
        function selMedida() { return { pat: '% de atipicos', n: 'Numero de registros', at: 'Registros atipicos', z: 'Valor z promedio' }[E.medida]; }
        correr();
    }

    ({ temporal: vista1, territorial: vista2, mapa: vista3, pivot: vista4 }[CFG.vista] || function () {})();
})();
