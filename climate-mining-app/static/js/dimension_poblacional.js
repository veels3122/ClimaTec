// ClimaTec - Etapa 4 / Dimension Poblacional.
// Dibuja los indicadores y las tres visualizaciones a partir del JSON que
// imprime la plantilla (#pob-datos), calculado en scripts/poblacional.py sobre
// clima_limpio.csv. No usa librerias externas ni imagenes: todo es DOM/SVG.
// Dos filtros: Anio (afecta indicadores y las 3 visualizaciones) y Categoria
// (afecta la visualizacion 1 y el indicador 2).

(function () {
    'use strict';

    var nodoDatos = document.getElementById('pob-datos');
    if (!nodoDatos) return;
    var D = JSON.parse(nodoDatos.textContent);

    var NS = 'http://www.w3.org/2000/svg';
    var COLORES = ['#49c7e0', '#ff6a4d', '#ffb454', '#3ddc97', '#c9b6ff', '#6a8bff'];

    // ---- Formato (es-CO: punto de miles, coma decimal) ----------------------
    function entero(n) { return Math.round(n).toLocaleString('es-CO'); }
    function dec(n, d) {
        return n.toLocaleString('es-CO', { minimumFractionDigits: d, maximumFractionDigits: d });
    }
    function pct(n, d) { return dec(n, d === undefined ? 1 : d) + '%'; }
    function pob(n) {
        if (n >= 1e9) return dec(n / 1e9, 2) + ' mil millones';
        if (n >= 1e6) return dec(n / 1e6, 1) + ' millones';
        return entero(n);
    }
    function el(id) { return document.getElementById(id); }
    function vaciar(nodo) { while (nodo.firstChild) nodo.removeChild(nodo.firstChild); }
    function crear(tag, clase, texto) {
        var n = document.createElement(tag);
        if (clase) n.className = clase;
        if (texto !== undefined) n.textContent = texto;
        return n;
    }
    function svg(tag, attrs) {
        var n = document.createElementNS(NS, tag);
        Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
        return n;
    }

    // ---- Estado -------------------------------------------------------------
    var estado = { anio: 'todos', cat: 'nivel_geografico' };
    var selAnio = el('pob-f-anio');
    var selCat = el('pob-f-cat');

    var opTodos = crear('option', '', 'Todos los anios (' + D.anios[0] + '-' + D.anios[D.anios.length - 1] + ')');
    opTodos.value = 'todos';
    selAnio.appendChild(opTodos);
    D.anios.forEach(function (a) {
        var o = crear('option', '', String(a));
        o.value = String(a);
        selAnio.appendChild(o);
    });
    D.categorias.forEach(function (c) {
        var o = crear('option', '', c.nombre);
        o.value = c.clave;
        selCat.appendChild(o);
    });

    function nombreCategoria(clave) {
        for (var i = 0; i < D.categorias.length; i++) {
            if (D.categorias[i].clave === clave) return D.categorias[i].nombre;
        }
        return clave;
    }

    // Poblacion solo existe para algunos anios: si el filtro cae fuera, se usa
    // el ultimo anio con dato y se avisa en pantalla.
    function anioPoblacion() {
        if (estado.anio !== 'todos' && D.poblacion[estado.anio]) return String(estado.anio);
        return String(D.anio_ref);
    }

    // ---- Tooltip ------------------------------------------------------------
    var tip = crear('div', 'pob-tip');
    tip.setAttribute('role', 'tooltip');
    tip.hidden = true;
    document.body.appendChild(tip);
    function mostrarTip(ev, texto) {
        tip.textContent = texto;
        tip.hidden = false;
        var x = ev.clientX + 14, y = ev.clientY + 14;
        var w = tip.offsetWidth, h = tip.offsetHeight;
        if (x + w > window.innerWidth - 8) x = ev.clientX - w - 14;
        if (y + h > window.innerHeight - 8) y = ev.clientY - h - 14;
        tip.style.left = x + 'px';
        tip.style.top = y + 'px';
    }
    function ocultarTip() { tip.hidden = true; }
    function conTip(nodo, texto) {
        nodo.addEventListener('mousemove', function (ev) { mostrarTip(ev, texto); });
        nodo.addEventListener('mouseleave', ocultarTip);
        nodo.addEventListener('focus', function () {
            var r = nodo.getBoundingClientRect();
            mostrarTip({ clientX: r.left + r.width / 2, clientY: r.top }, texto);
        });
        nodo.addEventListener('blur', ocultarTip);
    }

    function predominante(filas) {
        var top = null;
        filas.forEach(function (f) {
            if (/^Otros/.test(f.etiqueta)) return;
            if (!top || f.pct > top.pct) top = f;
        });
        return top;
    }

    // ---- Indicadores --------------------------------------------------------
    function renderIndicadores() {
        var clave = String(estado.anio);
        var total = D.registros_por_anio[clave];
        el('pob-i1-valor').textContent = entero(total);
        el('pob-i1-etq').textContent = estado.anio === 'todos'
            ? 'registros analizados (todos los anios)' : 'registros analizados en ' + estado.anio;
        el('pob-i1-sub').textContent = entero(D.entidades_por_anio[clave]) + ' entidades · ' +
            entero(D.indicadores_por_anio[clave]) + ' indicadores';

        var filas = D.registros[estado.cat][clave] || [];
        if (filas.length) {
            var top = predominante(filas);
            el('pob-i2-valor').textContent = pct(top.pct);
            el('pob-i2-etq').textContent = 'participacion de la categoria predominante';
            el('pob-i2-sub').textContent = nombreCategoria(estado.cat) + ': ' + top.etiqueta +
                ' (' + entero(top.n) + ' registros)';
        } else {
            el('pob-i2-valor').textContent = '-';
            el('pob-i2-sub').textContent = 'Sin registros para este filtro.';
        }

        var p = D.poblacion[anioPoblacion()];
        el('pob-i3-valor').textContent = pct(p.top5_pct);
        el('pob-i3-sub').textContent = p.top.slice(0, 5).map(function (t) { return t.entidad; }).join(', ') +
            ' · ' + p.anio;

        var nota = el('pob-nota-anio');
        if (estado.anio !== 'todos' && !D.poblacion[estado.anio]) {
            nota.textContent = 'La variable Poblacion solo existe para ' + D.anios_pob[0] + '-' +
                D.anios_pob[D.anios_pob.length - 1] + '; las visualizaciones 2 y 3 y el indicador 3 muestran ' +
                D.anio_ref + '.';
        } else if (estado.anio === 'todos') {
            nota.textContent = 'Con "Todos los anios", los registros cubren todo el periodo y la poblacion se muestra para ' +
                D.anio_ref + ' (ultimo anio con dato).';
        } else {
            nota.textContent = '';
        }
    }

    // ---- Visualizacion 1: barras horizontales de composicion ----------------
    function renderV1() {
        var clave = String(estado.anio);
        var filas = D.registros[estado.cat][clave] || [];
        var cont = el('pob-v1');
        vaciar(cont);
        var etq = estado.anio === 'todos' ? 'todos los anios' : estado.anio;
        el('pob-v1-titulo').textContent = 'Composicion de los registros por ' +
            nombreCategoria(estado.cat).toLowerCase();
        el('pob-v1-sub').textContent = entero(D.registros_por_anio[clave]) + ' registros · ' + etq;

        if (!filas.length) {
            cont.appendChild(crear('p', 'pob-mini', 'No hay registros para esta combinacion de filtros.'));
            el('pob-v1-lectura').textContent = '';
            return;
        }
        var top = predominante(filas);
        var max = Math.max.apply(null, filas.map(function (f) { return f.pct; })) || 1;
        filas.forEach(function (f) {
            var fila = crear('div', 'barra-h-fila' + (f === top ? ' warm' : ''));
            fila.tabIndex = 0;
            fila.appendChild(crear('div', 'barra-h-label', f.etiqueta));
            var track = crear('div', 'barra-h-track');
            var fill = crear('div', 'barra-h-fill');
            fill.style.width = '0%';
            track.appendChild(fill);
            fila.appendChild(track);
            fila.appendChild(crear('div', 'barra-h-val pob-val', pct(f.pct, 1) + ' · ' + entero(f.n)));
            cont.appendChild(fila);
            conTip(fila, f.etiqueta + ': ' + entero(f.n) + ' registros (' + pct(f.pct, 2) + ')');
            requestAnimationFrame(function () {
                requestAnimationFrame(function () {
                    fill.style.width = Math.max(100 * f.pct / max, 1.2) + '%';
                });
            });
        });

        var otras = filas.filter(function (f) { return f !== top; });
        var pctOtras = otras.reduce(function (a, f) { return a + f.pct; }, 0);
        var texto;
        if (top.pct >= 20) {
            texto = 'en ' + etq + ', la categoria "' + top.etiqueta + '" concentra ' + pct(top.pct) +
                ' de los registros y las otras ' + otras.length + ' suman ' + pct(pctOtras) + '.';
        } else {
            texto = 'en ' + etq + ' el reparto es parejo: la categoria mas frecuente ("' + top.etiqueta +
                '") tiene solo ' + pct(top.pct) + ' de los registros.';
        }
        el('pob-v1-lectura').textContent = 'Lectura del filtro actual: ' + texto;
    }

    // ---- Visualizacion 2: dona de regiones ----------------------------------
    function renderV2() {
        var p = D.poblacion[anioPoblacion()];
        var cont = el('pob-v2');
        var ley = el('pob-v2-leyenda');
        vaciar(cont); vaciar(ley);
        el('pob-v2-sub').textContent = 'Poblacion por region · ' + p.anio + ' · total ' + pob(p.regiones.reduce(function (a, r) { return a + r.poblacion; }, 0));

        var R = 78, C = 2 * Math.PI * R, grosor = 34;
        var s = svg('svg', { viewBox: '0 0 240 240', width: '100%', height: '100%', 'aria-hidden': 'true' });
        s.appendChild(svg('circle', { cx: 120, cy: 120, r: R, fill: 'none', stroke: 'rgba(255,255,255,.06)', 'stroke-width': grosor }));
        var acumulado = 0;
        var centroNum = crear('div', 'pob-dona-num', String(p.anio));
        var centroTxt = crear('div', 'pob-dona-txt', 'Poblacion mundial');
        var centro = crear('div', 'pob-dona-centro');
        centro.appendChild(centroNum); centro.appendChild(centroTxt);

        function restaurarCentro() { centroNum.textContent = String(p.anio); centroTxt.textContent = 'Poblacion mundial'; }

        p.regiones.forEach(function (r, i) {
            var largo = C * r.pct / 100;
            var arco = svg('circle', {
                cx: 120, cy: 120, r: R, fill: 'none', stroke: COLORES[i % COLORES.length],
                'stroke-width': grosor, 'stroke-dasharray': '0 ' + C,
                'stroke-dashoffset': -acumulado, transform: 'rotate(-90 120 120)', tabindex: '0',
                'class': 'pob-arco'
            });
            s.appendChild(arco);
            var texto = r.entidad + ': ' + pob(r.poblacion) + ' (' + pct(r.pct, 2) + ')';
            conTip(arco, texto);
            function activar() { centroNum.textContent = pct(r.pct); centroTxt.textContent = r.entidad; }
            arco.addEventListener('mouseenter', activar);
            arco.addEventListener('mouseleave', restaurarCentro);
            arco.addEventListener('focus', activar);
            arco.addEventListener('blur', restaurarCentro);
            var destino = Math.max(largo - 1.5, 0.8);
            requestAnimationFrame(function () {
                requestAnimationFrame(function () { arco.setAttribute('stroke-dasharray', destino + ' ' + (C - destino)); });
            });
            acumulado += largo;

            var li = crear('li');
            var sw = crear('i', 'pob-sw'); sw.style.background = COLORES[i % COLORES.length];
            li.appendChild(sw);
            li.appendChild(crear('span', 'pob-ley-nom', r.entidad));
            li.appendChild(crear('span', 'pob-ley-pob', pob(r.poblacion)));
            li.appendChild(crear('strong', 'pob-ley-pct', pct(r.pct)));
            ley.appendChild(li);
        });
        cont.appendChild(s);
        cont.appendChild(centro);

        var a = p.regiones[0], b = p.regiones[1];
        el('pob-v2-lectura').textContent = 'Lectura del filtro actual: en ' + p.anio + ', ' + a.entidad + ' (' +
            pct(a.pct) + ') y ' + b.entidad + ' (' + pct(b.pct) + ') suman ' + pct(a.pct + b.pct) +
            ' de la poblacion; la region minoritaria es ' + p.regiones[p.regiones.length - 1].entidad +
            ' (' + pct(p.regiones[p.regiones.length - 1].pct, 2) + ').';
    }

    // ---- Visualizacion 3: columnas agrupadas por tamano de pais -------------
    function renderV3() {
        var p = D.poblacion[anioPoblacion()];
        var cont = el('pob-v3');
        vaciar(cont);
        el('pob-v3-sub').textContent = p.paises + ' paises con dato de poblacion · ' + p.anio;

        var W = 560, H = 290, mI = 42, mD = 10, mS = 24, mInf = 46;
        var ancho = W - mI - mD, alto = H - mS - mInf;
        var s = svg('svg', { viewBox: '0 0 ' + W + ' ' + H, width: '100%', 'aria-hidden': 'true', 'class': 'pob-svg' });

        [0, 25, 50, 75, 100].forEach(function (v) {
            var y = mS + alto - alto * v / 100;
            s.appendChild(svg('line', { x1: mI, x2: W - mD, y1: y, y2: y, stroke: 'rgba(255,255,255,.08)' }));
            var t = svg('text', { x: mI - 8, y: y + 4, 'text-anchor': 'end', fill: 'rgba(244,247,251,.48)', 'font-size': 10 });
            t.textContent = v + '%';
            s.appendChild(t);
        });

        var n = p.grupos.length, banda = ancho / n, bw = Math.min(30, banda * 0.32);
        p.grupos.forEach(function (g, i) {
            var cx = mI + banda * i + banda / 2;
            var series = [
                { v: g.pct_paises, x: cx - bw - 2, color: '#49c7e0', nom: '% de los paises', extra: entero(g.paises) + ' paises' },
                { v: g.pct_pob, x: cx + 2, color: '#ff6a4d', nom: '% de la poblacion', extra: pob(g.poblacion) }
            ];
            series.forEach(function (sr) {
                var h = Math.max(alto * sr.v / 100, 1.5);
                var r = svg('rect', {
                    x: sr.x, y: mS + alto - h, width: bw, height: h, rx: 3, fill: sr.color, tabindex: '0',
                    'class': 'pob-col'
                });
                s.appendChild(r);
                conTip(r, g.grupo + ' · ' + sr.nom + ': ' + pct(sr.v, 2) + ' (' + sr.extra + ')');
                var lab = svg('text', {
                    x: sr.x + bw / 2, y: mS + alto - h - 5, 'text-anchor': 'middle',
                    fill: '#f4f7fb', 'font-size': 10, 'font-weight': 600
                });
                lab.textContent = pct(sr.v, sr.v < 10 ? 1 : 0);
                s.appendChild(lab);
            });
            var xl = svg('text', { x: cx, y: H - mInf + 20, 'text-anchor': 'middle', fill: 'rgba(244,247,251,.72)', 'font-size': 11 });
            xl.textContent = g.grupo;
            s.appendChild(xl);
        });
        cont.appendChild(s);

        var tb = el('pob-v3-tabla');
        vaciar(tb);
        p.grupos.forEach(function (g) {
            var tr = crear('tr');
            [
                [g.grupo, 'mono'], [entero(g.paises)], [pct(g.pct_paises, 1)], [pob(g.poblacion)], [pct(g.pct_pob, 1)],
                [g.co2_pc_mediana === null ? 'sin dato' : dec(g.co2_pc_mediana, 2) + ' t (n=' + g.co2_pc_n + ')']
            ].forEach(function (c) { tr.appendChild(crear('td', c[1] || '', c[0])); });
            tb.appendChild(tr);
        });

        var gran = p.grupos[p.grupos.length - 1], chico = p.grupos[0];
        el('pob-v3-lectura').textContent = 'Lectura del filtro actual: en ' + p.anio + ', los ' + gran.paises +
            ' paises de mas de 100 millones son ' + pct(gran.pct_paises) + ' de los paises y reunen ' + pct(gran.pct_pob) +
            ' de la poblacion; los ' + chico.paises + ' de menos de 1 millon reunen solo ' + pct(chico.pct_pob, 2) + '.';
    }

    // ---- Tabla de apoyo: caracteristicas generales y top 10 -----------------
    function renderPerfil() {
        var p = D.poblacion[anioPoblacion()];
        el('pob-p-sub').textContent = 'Paises con dato de poblacion · ' + p.anio;
        var tb = el('pob-perfil-tabla');
        vaciar(tb);
        var per = p.perfil;
        var filas = [
            ['Paises con dato de poblacion', entero(p.paises)],
            ['Poblacion sumada de los paises', pob(p.pob_paises)],
            ['Poblacion mundial (agregado World)', p.pob_mundo ? pob(p.pob_mundo) : 'sin dato'],
            ['Mediana por pais', pob(p.mediana)],
            ['Media por pais', pob(p.media)],
            ['Pais mas poblado', p.maximo.entidad + ' (' + pob(p.maximo.poblacion) + ')'],
            ['Pais menos poblado', p.minimo.entidad + ' (' + entero(p.minimo.poblacion) + ')'],
            ['CO2 per capita (mediana)', per.co2_pc.mediana === null ? 'sin dato' : dec(per.co2_pc.mediana, 2) + ' ' + per.co2_pc.unidad + ' · ' + per.co2_pc.n + ' paises'],
            ['GEI per capita (mediana)', per.gei_pc.mediana === null ? 'sin dato' : dec(per.gei_pc.mediana, 2) + ' ' + per.gei_pc.unidad + ' · ' + per.gei_pc.n + ' paises'],
            ['Energia per capita (mediana)', per.en_pc.mediana === null ? 'sin dato' : entero(per.en_pc.mediana) + ' ' + per.en_pc.unidad + ' · ' + per.en_pc.n + ' paises']
        ];
        filas.forEach(function (f) {
            var tr = crear('tr');
            tr.appendChild(crear('td', '', f[0]));
            tr.appendChild(crear('td', 'mono', f[1]));
            tb.appendChild(tr);
        });

        var tt = el('pob-top-tabla');
        vaciar(tt);
        p.top.forEach(function (t, i) {
            var tr = crear('tr');
            tr.appendChild(crear('td', 'mono', String(i + 1)));
            tr.appendChild(crear('td', '', t.entidad));
            tr.appendChild(crear('td', 'mono', pob(t.poblacion)));
            tr.appendChild(crear('td', 'mono', pct(t.pct, 1)));
            tt.appendChild(tr);
        });
        var tr = crear('tr', 'pob-fila-resto');
        tr.appendChild(crear('td', 'mono', '-'));
        tr.appendChild(crear('td', '', 'Resto (' + p.top_resto.paises + ' paises)'));
        tr.appendChild(crear('td', 'mono', pob(p.top_resto.poblacion)));
        tr.appendChild(crear('td', 'mono', pct(p.top_resto.pct, 1)));
        tt.appendChild(tr);
    }

    function renderTodo() {
        ocultarTip();
        renderIndicadores();
        renderV1();
        renderV2();
        renderV3();
        renderPerfil();
    }

    selAnio.addEventListener('change', function () { estado.anio = selAnio.value; renderTodo(); });
    selCat.addEventListener('change', function () { estado.cat = selCat.value; renderTodo(); });
    el('pob-f-reset').addEventListener('click', function () {
        estado.anio = 'todos'; estado.cat = 'nivel_geografico';
        selAnio.value = 'todos'; selCat.value = 'nivel_geografico';
        renderTodo();
    });

    renderTodo();
})();
