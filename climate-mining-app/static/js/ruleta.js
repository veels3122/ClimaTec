// ClimaTec — navegacion por etapas y secciones.
// Lee los datos desde los bloques JSON que imprime base.html con Jinja
// (asi los nombres y las URLs siempre vienen de url_for(), nunca se
// hardcodean aqui):
//
//   #ruleta-etapas-data                -> [{num, titulo, disponible, clave}] (5 etapas)
//   #ruleta-secciones-<clave>-data     -> {titulo, secciones: [{num, titulo, href, activo}]}
//                                          una por cada etapa disponible (hoy:
//                                          "definicion" con 8 secciones y
//                                          "recoleccion" con 7)
//
// Dos piezas de UI, cada una con su propia forma:
//   1) .etapas-rail   (riel vertical, en Inicio) — construirEtapasRail()
//   2) .rueda-secciones (donut SVG, en el overlay) — construirRuedaSecciones()
//
// El overlay de la rueda es UN solo componente compartido por todas las
// etapas disponibles: cada .ruleta-disparador trae data-etapa="<clave>" y,
// al abrirse, iniciarRuletaOverlay() carga el bloque JSON de esa clave.

(function () {
    'use strict';

    function leerJSON(id) {
        const el = document.getElementById(id);
        if (!el) return null;
        try { return JSON.parse(el.textContent); } catch (e) { return null; }
    }

    // ------------------------------------------------------------------
    // 1) Riel vertical de ETAPAS (Inicio)
    // ------------------------------------------------------------------
    function construirEtapasRail() {
        const cont = document.getElementById('etapas-rail');
        if (!cont) return;
        const etapas = leerJSON('ruleta-etapas-data') || [];
        const lista = document.createElement('ol');
        lista.className = 'etapas-rail-lista';

        etapas.forEach((e) => {
            const li = document.createElement('li');
            li.className = 'etapas-rail-item' + (e.disponible ? ' es-activa' : '');

            const nodo = document.createElement(e.disponible ? 'button' : 'span');
            nodo.className = 'etapas-rail-nodo' + (e.disponible ? ' ruleta-disparador' : '');
            nodo.textContent = e.num;
            if (e.disponible) {
                nodo.type = 'button';
                if (e.clave) nodo.dataset.etapa = e.clave;
                nodo.setAttribute('aria-haspopup', 'dialog');
                nodo.setAttribute('aria-expanded', 'false');
                nodo.setAttribute('aria-label', 'Abrir secciones de ' + e.titulo);
            } else {
                nodo.setAttribute('aria-disabled', 'true');
            }

            const nombre = document.createElement('span');
            nombre.className = 'etapas-rail-nombre';
            nombre.innerHTML = e.titulo + (e.disponible ? '' : '<span class="etapas-rail-tag">proximamente</span>');

            li.appendChild(nodo);
            li.appendChild(nombre);
            lista.appendChild(li);
        });
        cont.appendChild(lista);
    }

    // ------------------------------------------------------------------
    // 2) Rueda circular (donut) de SECCIONES
    // ------------------------------------------------------------------
    const SVG_NS = 'http://www.w3.org/2000/svg';
    const CX = 120, CY = 120, R_OUT = 100, R_IN = 52, GAP_DEG = 2.2;

    function puntoEnCirculo(r, anguloDeg) {
        const rad = (anguloDeg - 90) * Math.PI / 180;
        return { x: CX + r * Math.cos(rad), y: CY + r * Math.sin(rad) };
    }

    function pathGajo(anguloIni, anguloFin) {
        const p1 = puntoEnCirculo(R_OUT, anguloIni);
        const p2 = puntoEnCirculo(R_OUT, anguloFin);
        const p3 = puntoEnCirculo(R_IN, anguloFin);
        const p4 = puntoEnCirculo(R_IN, anguloIni);
        const largeArc = (anguloFin - anguloIni) > 180 ? 1 : 0;
        return [
            'M', p1.x, p1.y,
            'A', R_OUT, R_OUT, 0, largeArc, 1, p2.x, p2.y,
            'L', p3.x, p3.y,
            'A', R_IN, R_IN, 0, largeArc, 0, p4.x, p4.y,
            'Z',
        ].join(' ');
    }

    function construirRuedaSecciones(svgEl, centroNumEl, centroTituloEl, secciones) {
        svgEl.innerHTML = '';
        const n = secciones.length;
        const paso = 360 / n;
        const tituloDefecto = centroTituloEl.textContent;
        const numDefecto = centroNumEl.textContent;

        secciones.forEach((s, i) => {
            const ini = i * paso + GAP_DEG / 2;
            const fin = (i + 1) * paso - GAP_DEG / 2;
            const medio = (ini + fin) / 2;

            const gajo = document.createElementNS(SVG_NS, 'path');
            gajo.setAttribute('d', pathGajo(ini, fin));
            gajo.setAttribute('class', 'gajo' + (s.activo ? ' es-actual' : ''));
            gajo.setAttribute('tabindex', '0');
            gajo.setAttribute('role', 'link');
            gajo.setAttribute('aria-label', s.num + '. ' + s.titulo);

            // Direccion radial para el pequeno "pop" al pasar el mouse
            const dir = puntoEnCirculo(1, medio);
            gajo.style.setProperty('--gdx', ((dir.x - CX) * 4) + 'px');
            gajo.style.setProperty('--gdy', ((dir.y - CY) * 4) + 'px');

            const mostrar = () => {
                centroNumEl.textContent = String(s.num).padStart(2, '0') + ' / ' + String(n).padStart(2, '0');
                centroTituloEl.textContent = s.titulo;
            };
            const ocultar = () => {
                centroNumEl.textContent = numDefecto;
                centroTituloEl.textContent = tituloDefecto;
            };
            const ir = () => { window.location.href = s.href; };

            gajo.addEventListener('mouseenter', mostrar);
            gajo.addEventListener('focus', mostrar);
            gajo.addEventListener('mouseleave', ocultar);
            gajo.addEventListener('blur', ocultar);
            gajo.addEventListener('click', ir);
            gajo.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); ir(); }
            });

            const numTxt = puntoEnCirculo((R_OUT + R_IN) / 2, medio);
            const texto = document.createElementNS(SVG_NS, 'text');
            texto.setAttribute('x', numTxt.x);
            texto.setAttribute('y', numTxt.y);
            texto.setAttribute('class', 'gajo-num');
            texto.textContent = s.num;

            svgEl.appendChild(gajo);
            svgEl.appendChild(texto);
        });
    }

    // ------------------------------------------------------------------
    // 3) Overlay que aloja la rueda (topbar, menu movil, o riel de Inicio)
    // ------------------------------------------------------------------
    function iniciarRuletaOverlay() {
        const overlayFondo = document.querySelector('.ruleta-overlay-fondo');
        if (!overlayFondo) return;

        const panel = overlayFondo.querySelector('.ruleta-overlay-panel');
        const svgEl = panel.querySelector('.rueda-secciones');
        const centroNumEl = panel.querySelector('.rueda-secciones-num');
        const centroTituloEl = panel.querySelector('.rueda-secciones-titulo');
        const tituloEl = panel.querySelector('.ruleta-titulo');
        const placeholderCentro = centroTituloEl.textContent;
        const cerrarBtn = panel.querySelector('.ruleta-overlay-cerrar');

        // El overlay es un solo componente reutilizado por cada etapa
        // disponible: abrir(clave) busca el bloque JSON
        // #ruleta-secciones-<clave>-data (impreso por base.html) y arma la
        // rueda con esas secciones. Si la clave no trae datos, no hace nada
        // (evita un overlay vacio).
        function abrir(clave) {
            const datos = leerJSON('ruleta-secciones-' + clave + '-data');
            if (!datos || !datos.secciones || !datos.secciones.length) return;

            tituloEl.textContent = datos.titulo;
            panel.setAttribute('aria-label', 'Secciones de la etapa ' + datos.titulo);
            centroNumEl.textContent = '01–' + String(datos.secciones.length).padStart(2, '0');
            centroTituloEl.textContent = placeholderCentro;

            construirRuedaSecciones(svgEl, centroNumEl, centroTituloEl, datos.secciones);
            overlayFondo.classList.add('abierto');
            document.querySelectorAll('.ruleta-disparador').forEach((b) => b.setAttribute('aria-expanded', 'true'));
            document.body.style.overflow = 'hidden';
        }
        function cerrar() {
            overlayFondo.classList.remove('abierto');
            document.querySelectorAll('.ruleta-disparador').forEach((b) => b.setAttribute('aria-expanded', 'false'));
            document.body.style.overflow = '';
        }
        // Delegado: cualquier .ruleta-disparador presente HOY o agregado
        // dinamicamente (el nodo activo del riel de Inicio se crea en JS)
        // abre el overlay con la etapa que traiga en data-etapa.
        document.addEventListener('click', (e) => {
            const disparador = e.target.closest('.ruleta-disparador');
            if (disparador) abrir(disparador.dataset.etapa || 'definicion');
        });
        if (cerrarBtn) cerrarBtn.addEventListener('click', cerrar);
        overlayFondo.addEventListener('click', (e) => { if (e.target === overlayFondo) cerrar(); });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && overlayFondo.classList.contains('abierto')) cerrar();
        });
    }

    document.addEventListener('DOMContentLoaded', () => {
        construirEtapasRail();
        iniciarRuletaOverlay();
    });
})();
