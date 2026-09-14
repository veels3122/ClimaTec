// ClimaTec — fondos animados por seccion (Definicion y Recoleccion de Datos).
// Un pequeno "motor" comun (resize con devicePixelRatio + requestAnimationFrame,
// apagado si el usuario pide "reduced motion") y una funcion de dibujo por
// seccion, elegida segun el atributo data-fondo del .page-hero. Cada seccion
// nueva que se integre repite el mismo patron: una metafora visual propia,
// ligada a su contenido real (nunca un fondo generico repetido).
// Todo en Canvas 2D puro: sin librerias, sin video, sin imagenes externas.

(function () {
    'use strict';

    const REDUCIDO = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    const PALETA = {
        frio: '#49c7e0',
        calido: '#ff6a4d',
        ambar: '#ffb454',
        ok: '#3ddc97',
        morado: '#c9b6ff',
        blanco: 'rgba(255,255,255,',
    };

    // El mapa de "Fuentes de datos" se dibuja DENTRO del propio canvas (no
    // solo como imagen de fondo en CSS) porque los iconos de cada
    // institucion se calculan por lat/lon real convertida a fraccion del
    // mapa -- si el mapa se mostrara con "cover" en un .page-hero de otra
    // proporcion, se recortaria y los iconos quedarian desalineados de su
    // pais real. Dibujandolo aqui con la MISMA cuenta de "contain" que se
    // usa para ubicar los iconos, la alineacion queda garantizada sin
    // importar la proporcion de pantalla.
    const mapaFuentes = new Image();
    mapaFuentes.src = '/static/img/fondos/fuentes.jpg';
    let mapaFuentesListo = false;
    mapaFuentes.addEventListener('load', () => { mapaFuentesListo = true; });

    function rectMapaFuentes(w, h) {
        const proporcion = mapaFuentesListo
            ? mapaFuentes.naturalWidth / mapaFuentes.naturalHeight
            : 2000 / 989;
        // "contain": el mapa completo siempre visible, sin recorte.
        const escalaAncho = w / (proporcion * h);
        let dw, dh;
        if (escalaAncho >= 1) {
            // el alto es el limitante: el mapa llena el alto completo
            dh = h; dw = h * proporcion;
        } else {
            // el ancho es el limitante: el mapa llena el ancho completo
            dw = w; dh = w / proporcion;
        }
        return { x: (w - dw) / 2, y: (h - dh) / 2, w: dw, h: dh };
    }

    function motor(canvas, dibujar, { fija = false } = {}) {
        const ctx = canvas.getContext('2d');
        let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);

        function medir() {
            const rect = fija
                ? { width: window.innerWidth, height: window.innerHeight }
                : canvas.parentElement.getBoundingClientRect();
            w = Math.max(1, Math.round(rect.width));
            h = Math.max(1, Math.round(rect.height));
            canvas.width = w * dpr;
            canvas.height = h * dpr;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }
        medir();
        window.addEventListener('resize', medir);

        let inicio = performance.now();
        function frame(ahora) {
            // Math.max(0, ...): el timestamp que entrega requestAnimationFrame
            // puede corresponder a un instante ANTERIOR al performance.now()
            // que capturamos en "inicio" (es una particularidad conocida del
            // primer frame). Sin este clamp, "t" podia salir levemente
            // negativo una sola vez y algunas formas (radios de circulo,
            // etc.) recibian un valor negativo y Canvas2D lanzaba una
            // excepcion ("radius provided is negative").
            const t = Math.max(0, (ahora - inicio) / 1000);
            dibujar(ctx, w, h, t);
            if (!REDUCIDO) requestAnimationFrame(frame);
        }
        if (REDUCIDO) {
            dibujar(ctx, w, h, 0);
        } else {
            requestAnimationFrame(frame);
        }
    }

    function lerp(a, b, t) { return a + (b - a) * t; }
    function clamp01(x) { return Math.max(0, Math.min(1, x)); }
    function easeInOutSine(t) { return -(Math.cos(Math.PI * t) - 1) / 2; }

    // ------------------------------------------------------------------
    // 1) PROBLEMA Y CONTEXTO — bandas de calentamiento ("warming stripes")
    // que laten desde un nucleo, con particulas de CO2 subiendo. Referencia
    // directa a la propia metafora visual del proyecto.
    // ------------------------------------------------------------------
    function fondoProblema(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        // Centro ajustado al foco de luz real de problema.jpg (medido por
        // brillo sobre la foto: ~0.735w, 0.526h) -- antes quedaba mas
        // abajo y a la derecha del resplandor real de la chimenea.
        const cx = w * 0.74, cy = h * 0.53;
        const bandas = 7;
        for (let i = bandas; i >= 0; i--) {
            const fase = (t * 0.12 + i / bandas) % 1;
            const r = Math.max(0, fase * Math.max(w, h) * 0.95);
            const mezcla = i / bandas;
            const color = i % 2 === 0 ? PALETA.frio : PALETA.calido;
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.strokeStyle = color;
            ctx.globalAlpha = (1 - fase) * 0.22;
            ctx.lineWidth = 14;
            ctx.stroke();
        }
        ctx.globalAlpha = 1;
        // Particulas de CO2 subiendo
        const n = 26;
        for (let i = 0; i < n; i++) {
            const semilla = i * 37.13;
            const x = (Math.sin(semilla) * 0.5 + 0.5) * w;
            const velocidad = 18 + (i % 5) * 6;
            const y = h - ((t * velocidad + semilla * 40) % (h + 40));
            const r = 1.4 + (i % 3);
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.blanco + (0.12 + 0.1 * Math.sin(t + i)) + ')';
            ctx.fill();
        }
    }

    // ------------------------------------------------------------------
    // 2) PREGUNTAS — El Nino vs La Nina "peleando" mientras el CO2 sube
    // fuerte y luego baja gradualmente. Controlado por el SCROLL de toda
    // la pagina (no por tiempo), via el progreso global calculado en
    // calcularProgresoScroll().
    // ------------------------------------------------------------------
    function fondoPreguntas(ctx, w, h, t, progreso) {
        // OJO: antes esta funcion pintaba aqui un rectangulo OPACO
        // ("#05070f" a pantalla completa) antes de dibujar los blobs. Este
        // canvas vive en z-index:-3, ARRIBA de las fotos reales de El Nino/
        // La Nina (z-index:-4, ver fondos.css) -- un relleno opaco tapaba
        // por completo esas fotos, que quedaban 100% invisibles detras del
        // canvas (por eso se veia "solo negro con manchas de color", el bug
        // que reporto Mateo). Con clearRect (transparente) el canvas deja
        // ver la foto real de fondo y solo se dibujan encima los blobs y
        // particulas semitransparentes, como esta pensado.
        ctx.clearRect(0, 0, w, h);

        // Envolvente asimetrica: sube rapido, baja gradual (nunca de golpe).
        const p = progreso == null ? 0 : progreso;
        let envolvente;
        if (p < 0.7) {
            envolvente = Math.pow(p / 0.7, 1.4);
        } else {
            envolvente = 1 - easeInOutSine((p - 0.7) / 0.3) * 0.55;
        }

        const pelea = Math.sin(t * 0.9) * 0.5 + 0.5; // quien domina ahora
        const ninoX = lerp(w * 0.28, w * 0.5, pelea) ;
        const ninaX = lerp(w * 0.72, w * 0.5, pelea);
        const radioBase = Math.min(w, h) * (0.22 + 0.1 * envolvente);

        function blob(x, y, r, color, alpha) {
            const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
            grad.addColorStop(0, color);
            grad.addColorStop(1, 'transparent');
            ctx.globalAlpha = alpha;
            ctx.fillStyle = grad;
            ctx.beginPath();
            ctx.arc(x, y, r, 0, Math.PI * 2);
            ctx.fill();
        }
        blob(ninoX, h * 0.42, radioBase * (0.85 + 0.3 * pelea), PALETA.calido, 0.55);
        blob(ninaX, h * 0.58, radioBase * (1.15 - 0.3 * pelea), PALETA.frio, 0.5);

        // Haz de calor de CO2 creciendo con la envolvente
        ctx.globalAlpha = 0.18 + 0.4 * envolvente;
        const g = ctx.createLinearGradient(0, h, 0, 0);
        g.addColorStop(0, 'rgba(255,106,77,.55)');
        g.addColorStop(1, 'transparent');
        ctx.fillStyle = g;
        ctx.fillRect(0, h * (1 - envolvente * 0.6), w, h * envolvente * 0.6);

        // Particulas de CO2, cantidad segun la envolvente
        const nMax = 46;
        const n = Math.round(6 + nMax * envolvente);
        ctx.globalAlpha = 1;
        for (let i = 0; i < n; i++) {
            const semilla = i * 12.9;
            const x = ((Math.sin(semilla) * 0.5 + 0.5) * w + t * 6) % w;
            const y = h - ((t * (20 + (i % 6) * 5) + semilla * 50) % h);
            ctx.beginPath();
            ctx.arc(x, y, 1.6, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,180,84,' + (0.15 + 0.35 * envolvente) + ')';
            ctx.fill();
        }
    }

    function calcularProgresoScroll() {
        const doc = document.documentElement;
        const total = doc.scrollHeight - window.innerHeight;
        if (total <= 0) return 0;
        return clamp01(window.scrollY / total);
    }

    // ------------------------------------------------------------------
    // 3) NECESIDADES DE INFORMACION — red de nodos convergiendo a un
    // nodo central (la pregunta), con pulsos viajando por cada arista.
    // ------------------------------------------------------------------
    function fondoNecesidades(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        // Centro ajustado al foco real de necesidades.jpg (medido por
        // brillo: ~0.706w, 0.518h), donde estan las pantallas/consola.
        const cx = w * 0.72, cy = h * 0.52;
        const etiquetas = ['Entidades', 'Variables', 'Periodo', 'Cobertura', 'Granularidad', 'Integracion'];
        const radio = Math.min(w, h) * 0.34;
        const nodos = etiquetas.map((txt, i) => {
            const ang = (i / etiquetas.length) * Math.PI * 2 + t * 0.05;
            return { x: cx + Math.cos(ang) * radio, y: cy + Math.sin(ang) * radio * 0.62, txt };
        });

        nodos.forEach((n) => {
            ctx.beginPath();
            ctx.moveTo(n.x, n.y);
            ctx.lineTo(cx, cy);
            ctx.strokeStyle = 'rgba(73,199,224,.18)';
            ctx.lineWidth = 1.4;
            ctx.stroke();

            const fase = (t * 0.35 + n.x * 0.01) % 1;
            const px = lerp(n.x, cx, fase);
            const py = lerp(n.y, cy, fase);
            ctx.beginPath();
            ctx.arc(px, py, 2.6, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.ambar;
            ctx.fill();

            ctx.beginPath();
            ctx.arc(n.x, n.y, 5, 0, Math.PI * 2);
            ctx.fillStyle = 'rgba(255,255,255,.85)';
            ctx.fill();

            ctx.font = '11px "IBM Plex Mono", monospace';
            ctx.fillStyle = 'rgba(255,255,255,.55)';
            ctx.textAlign = n.x > cx ? 'left' : 'right';
            ctx.fillText(n.txt, n.x + (n.x > cx ? 9 : -9), n.y + 4);
        });

        ctx.beginPath();
        ctx.arc(cx, cy, 12 + Math.sin(t * 2) * 2, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,106,77,.85)';
        ctx.fill();
    }

    // ------------------------------------------------------------------
    // 4) FUENTES DE DATOS — mapa REAL equirectangular (fuentes.jpg) con
    // cada institucion representada por un ICONO propio (no un punto
    // generico) en su posicion geografica verdadera, y Colombia marcada
    // como la SEDE DEL PROYECTO: ya no convergen hacia un punto arbitrario
    // en la mitad del mar, sino hacia Bogota, que es donde real y
    // efectivamente se hace el analisis. De cada fuente externa (OWID,
    // NOAA, UNFCCC) sale un flujo CONSTANTE de varias particulas (no una
    // sola en loop) viajando hacia Colombia, como datos entrando sin
    // parar. IDEAM y UNGRD ya estan en Colombia, asi que se dibujan como
    // parte del propio nodo local, sin linea larga.
    //
    // Posiciones calculadas con proyeccion equirectangular a partir de
    // lat/lon reales (formula: x = (lon+180)/360, y = (90-lat)/180):
    //   OWID   -> Oxford, Reino Unido     (51.75 N, -1.25)
    //   IDEAM  -> Bogota, Colombia        (4.71 N, -74.07)
    //   NOAA   -> Silver Spring, EE.UU.   (38.99 N, -76.94)
    //   UNGRD  -> Bogota, Colombia        (3.50 N, -72.50 — desplazado un
    //             poco de IDEAM para que los dos pines no se encimen)
    //   UNFCCC -> Bonn, Alemania          (50.73 N, 7.10)
    // ------------------------------------------------------------------
    function dibujarIconoFuente(tipo, ctx, x, y, r, color) {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.fillStyle = color;
        ctx.lineWidth = 1.3;
        if (tipo === 'db') {
            // OWID — base de datos: cilindro (dos elipses + laterales)
            ctx.beginPath();
            ctx.ellipse(x, y - r * 0.4, r * 0.62, r * 0.26, 0, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x - r * 0.62, y - r * 0.4); ctx.lineTo(x - r * 0.62, y + r * 0.4);
            ctx.moveTo(x + r * 0.62, y - r * 0.4); ctx.lineTo(x + r * 0.62, y + r * 0.4);
            ctx.stroke();
            ctx.beginPath();
            ctx.ellipse(x, y + r * 0.4, r * 0.62, r * 0.26, 0, 0, Math.PI);
            ctx.stroke();
        } else if (tipo === 'satelite') {
            // NOAA — plato satelital + mastil receptor
            ctx.beginPath();
            ctx.arc(x, y, r * 0.65, Math.PI * 1.1, Math.PI * 1.9);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x, y - r * 0.1); ctx.lineTo(x + r * 0.5, y - r * 0.78);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(x + r * 0.5, y - r * 0.78, 1.4, 0, Math.PI * 2);
            ctx.fill();
        } else if (tipo === 'documento') {
            // UNFCCC — documento/acuerdo: hoja con lineas de texto
            const rw = r * 1.05, rh = r * 1.25;
            ctx.beginPath();
            if (ctx.roundRect) ctx.roundRect(x - rw / 2, y - rh / 2, rw, rh, 2);
            else ctx.rect(x - rw / 2, y - rh / 2, rw, rh);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x - rw * 0.28, y - rh * 0.12); ctx.lineTo(x + rw * 0.28, y - rh * 0.12);
            ctx.moveTo(x - rw * 0.28, y + rh * 0.12); ctx.lineTo(x + rw * 0.1, y + rh * 0.12);
            ctx.stroke();
        } else if (tipo === 'estacion') {
            // IDEAM — mini estacion meteorologica (mastil + anemometro)
            ctx.beginPath();
            ctx.moveTo(x, y + r * 0.7); ctx.lineTo(x, y - r * 0.3);
            ctx.stroke();
            ctx.beginPath();
            ctx.arc(x, y - r * 0.55, r * 0.3, 0, Math.PI * 2);
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(x - r * 0.45, y); ctx.lineTo(x + r * 0.45, y);
            ctx.stroke();
        } else if (tipo === 'escudo') {
            // UNGRD — escudo (gestion de riesgo/emergencias)
            ctx.beginPath();
            ctx.moveTo(x, y - r * 0.78);
            ctx.lineTo(x + r * 0.6, y - r * 0.36);
            ctx.lineTo(x + r * 0.6, y + r * 0.22);
            ctx.quadraticCurveTo(x + r * 0.6, y + r * 0.75, x, y + r * 0.92);
            ctx.quadraticCurveTo(x - r * 0.6, y + r * 0.75, x - r * 0.6, y + r * 0.22);
            ctx.lineTo(x - r * 0.6, y - r * 0.36);
            ctx.closePath();
            ctx.stroke();
        }
        ctx.restore();
    }

    function dibujarSedeColombia(ctx, x, y, r) {
        // Marcador de la sede del proyecto: estrella de 5 puntas en color
        // calido (contraste deliberado frente al verde de las fuentes
        // externas), mas grande que cualquier otro icono del mapa.
        ctx.save();
        ctx.beginPath();
        for (let i = 0; i < 10; i++) {
            const ang = (i / 10) * Math.PI * 2 - Math.PI / 2;
            const rr = i % 2 === 0 ? r : r * 0.45;
            const px = x + Math.cos(ang) * rr, py = y + Math.sin(ang) * rr;
            i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
        }
        ctx.closePath();
        ctx.fillStyle = PALETA.calido;
        ctx.globalAlpha = 0.92;
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,255,255,.85)';
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.globalAlpha = 1;
        ctx.restore();
    }

    // Cuanto se acerca el mapa respecto al "contain" base (mapa completo
    // visible). Mateo pidio "un poquito mas de zoom" porque el mapa
    // completo distorsionaba alguito el diseno y no se alcanzaban a ver
    // bien los lugares de origen de los datos -- 1.16 = 16% mas grande.
    const ZOOM_MAPA_FUENTES = 1.30;
    // Punto de anclaje del zoom, en FRACCION DEL MAPA COMPLETO (0..1, las
    // mismas fracciones lat/lon que usan los pines) -- es el centro de
    // masa real de Colombia + las 5 fuentes (OWID/NOAA/UNFCCC/IDEAM/UNGRD),
    // no el centro geometrico del mapa (que caeria en el golfo de Guinea,
    // vacio). Anclando el zoom aqui, la region que realmente importa queda
    // fija en pantalla mientras el resto del mapa crece alrededor -- nunca
    // se sale del encuadre ni empuja los pines fuera de la pantalla.
    const ANCLA_ZOOM_FUENTES = { x: 0.361, y: 0.359 };

    function fondoFuentes(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);

        // El mapa se dibuja aqui mismo (ver rectMapaFuentes) para que los
        // iconos usen exactamente el mismo rectangulo/escala que la imagen
        // -- asi coinciden con su pais real sin importar la proporcion de
        // pantalla. Mientras el archivo no ha cargado, se deja el fondo
        // heredado (degradado + fondo-foto-fuentes en CSS) sin dibujar mapa.
        // rectMapaFuentes() da el "contain" base (mapa COMPLETO, sin
        // recorte); a partir de ahi se aplica un zoom leve anclado en
        // ANCLA_ZOOM_FUENTES. Como px()/py() (mas abajo) siguen siendo
        // "mapa.x + fraccion*mapa.w", agrandar/mover este rectangulo NO
        // desalinea ningun pin -- la formula es la misma, solo cambia la
        // magnitud del rectangulo sobre el que se aplica.
        const base = rectMapaFuentes(w, h);
        const mapa = {
            w: base.w * ZOOM_MAPA_FUENTES,
            h: base.h * ZOOM_MAPA_FUENTES,
        };
        // Ancla: el punto ANCLA_ZOOM_FUENTES debe quedar en la MISMA
        // posicion de pantalla antes y despues del zoom.
        const anclaPantallaX = base.x + ANCLA_ZOOM_FUENTES.x * base.w;
        const anclaPantallaY = base.y + ANCLA_ZOOM_FUENTES.y * base.h;
        mapa.x = anclaPantallaX - ANCLA_ZOOM_FUENTES.x * mapa.w;
        mapa.y = anclaPantallaY - ANCLA_ZOOM_FUENTES.y * mapa.h;

        if (mapaFuentesListo) {
            ctx.drawImage(mapaFuentes, mapa.x, mapa.y, mapa.w, mapa.h);
            // Mismo tinte (color + opacidad + mezcla "multiply") que
            // .fondo-foto-tinte usa para acento-ok en el resto del sitio,
            // replicado aqui para que tambien cubra el mapa recien dibujado.
            const tinte = ctx.createLinearGradient(mapa.x, mapa.y, mapa.x + mapa.w * 0.6, mapa.y + mapa.h);
            tinte.addColorStop(0, 'rgba(61,220,151,.3)');
            tinte.addColorStop(1, 'rgba(5,7,15,.85)');
            ctx.save();
            ctx.globalCompositeOperation = 'multiply';
            ctx.globalAlpha = 0.55;
            ctx.fillStyle = tinte;
            ctx.fillRect(mapa.x, mapa.y, mapa.w, mapa.h);
            ctx.restore();
        }

        // Conversion lat/lon -> posicion real DENTRO del rectangulo del
        // mapa (no del canvas completo): px = mapa.x + fx*mapa.w, etc.
        const px = (fx) => mapa.x + fx * mapa.w;
        const py = (fy) => mapa.y + fy * mapa.h;

        // Colombia = sede del proyecto. Todo converge aqui, no en un punto
        // generico del oceano.
        const colombia = { x: px(0.287), y: py(0.498) };

        // OWID (Oxford) y UNFCCC (Bonn) quedan muy cerca entre si en el
        // mapa real (~700km) -- sus etiquetas se separan a los lados
        // (izquierda/derecha) en vez de las tres arriba centradas, para
        // que no se encimen.
        const fuentesExternas = [
            { x: 0.4795, y: 0.2255, nombre: 'OWID', icono: 'db', etiqueta: 'izquierda' },
            { x: 0.5058, y: 0.2262, nombre: 'UNFCCC', icono: 'documento', etiqueta: 'derecha' },
            { x: 0.08, y: 0.39, nombre: 'NOAA GML', icono: 'satelite', etiqueta: 'arriba' },   
            { x: 0.2988, y: 0.2874, nombre: 'NASA GISS', icono: 'satelite', etiqueta: 'arriba' },
            { x: 0.2348, y: 0.2424, nombre: 'BANCO MUNDIAL', icono: 'documento', etiqueta: 'izquierda' },
            { x: 0.2468, y: 0.3350, nombre: 'NASA POWER', icono: 'satelite', etiqueta: 'derecha' },
            { x: 0.2038, y: 0.2984, nombre: 'NOAA NCEI', icono: 'db', etiqueta: 'abajo' },
        ];
        // IDEAM y UNGRD estan a solo unos km entre si (ambas en Bogota), tan
        // cerca del propio marcador de la sede que sus iconos quedarian
        // tapados debajo de la estrella si se usara su lat/lon exacta --
        // se separan un poco visualmente alrededor del hub (arriba-izq /
        // abajo-izq), y sus etiquetas ademas se desfasan para no encimarse
        // entre si ni con "COLOMBIA - sede del proyecto".
        const fuentesLocales = [
            { x: 0.284, y: 0.456, nombre: 'IDEAM', icono: 'estacion', dyEtiqueta: -13 },
            { x: 0.288, y: 0.504, nombre: 'UNGRD', icono: 'escudo', dyEtiqueta: 9 },
        ];

        // Halo de la sede, pulsando por debajo de todo lo demas.
        const radioHalo = (16 + Math.sin(t * 1.6) * 4) * 2.4;
        const halo = ctx.createRadialGradient(colombia.x, colombia.y, 0, colombia.x, colombia.y, radioHalo);
        halo.addColorStop(0, 'rgba(255,106,77,.32)');
        halo.addColorStop(1, 'transparent');
        ctx.fillStyle = halo;
        ctx.beginPath();
        ctx.arc(colombia.x, colombia.y, radioHalo, 0, Math.PI * 2);
        ctx.fill();

        // Cada fuente externa manda un flujo CONSTANTE (3 particulas
        // desfasadas, no una sola) de datos viajando hacia Colombia.
        fuentesExternas.forEach((f, i) => {
            const x = px(f.x), y = py(f.y);
            ctx.beginPath();
            ctx.moveTo(x, y);
            ctx.lineTo(colombia.x, colombia.y);
            ctx.strokeStyle = 'rgba(61,220,151,.16)';
            ctx.lineWidth = 1;
            ctx.stroke();

            const nParticulas = 3;
            for (let p = 0; p < nParticulas; p++) {
                const fase = (t * 0.22 + i * 0.15 + p / nParticulas) % 1;
                const px = lerp(x, colombia.x, fase);
                const py = lerp(y, colombia.y, fase);
                ctx.beginPath();
                ctx.arc(px, py, 2.2, 0, Math.PI * 2);
                ctx.fillStyle = PALETA.ok;
                ctx.globalAlpha = 0.85 - fase * 0.35;
                ctx.fill();
            }
            ctx.globalAlpha = 1;

            const pulsoLocal = 6 + Math.sin(t * 2.4 + i) * 1.5;
            ctx.beginPath();
            ctx.arc(x, y, pulsoLocal + 7, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(73,199,224,.4)';
            ctx.lineWidth = 1.2;
            ctx.stroke();

            dibujarIconoFuente(f.icono, ctx, x, y, 9, 'rgba(255,255,255,.92)');

                       ctx.font = '10px "IBM Plex Mono", monospace';
            ctx.fillStyle = 'rgba(255,255,255,.6)';
            if (f.etiqueta === 'izquierda') {
                ctx.textAlign = 'right';
                ctx.fillText(f.nombre, x - pulsoLocal - 10, y + 3);
            } else if (f.etiqueta === 'derecha') {
                ctx.textAlign = 'left';
                ctx.fillText(f.nombre, x + pulsoLocal + 10, y + 3);
            } else if (f.etiqueta === 'abajo') {
                ctx.textAlign = 'center';
                ctx.fillText(f.nombre, x, y + pulsoLocal + 16);
            } else {
                ctx.textAlign = 'center';
                ctx.fillText(f.nombre, x, y - pulsoLocal - 12);
            }
        });

        // IDEAM y UNGRD ya estan en Colombia: solo su icono local, sin
        // linea larga (irian de largo casi cero).
        fuentesLocales.forEach((f) => {
            const x = px(f.x), y = py(f.y);
            dibujarIconoFuente(f.icono, ctx, x, y, 8, 'rgba(255,255,255,.9)');
            ctx.font = '9px "IBM Plex Mono", monospace';
            ctx.fillStyle = 'rgba(255,255,255,.55)';
            ctx.textAlign = 'right';
            ctx.fillText(f.nombre, x - 11, y + f.dyEtiqueta);
        });

        dibujarSedeColombia(ctx, colombia.x, colombia.y, 11 + Math.sin(t * 1.6) * 1.5);
        // La etiqueta va a la DERECHA de la estrella (no centrada debajo):
        // Colombia cae del lado izquierdo de cualquier mapa del mundo
        // centrado en Greenwich, el mismo lado donde vive el texto de la
        // pagina (titulo/parrafo) -- ponerla a la derecha la aleja de esa
        // columna en vez de competir con el encabezado.
        ctx.font = '600 11px "IBM Plex Mono", monospace';
        ctx.fillStyle = 'rgba(255,180,84,.95)';
        ctx.textAlign = 'left';
        ctx.fillText('COLOMBIA · sede del proyecto', colombia.x + 20, colombia.y + 4);
    }

    // ------------------------------------------------------------------
    // 5) DATASET — filas de celdas consolidandose desde los lados hacia
    // el centro, como si varias fuentes se unieran en una sola tabla.
    // ------------------------------------------------------------------
    function fondoDataset(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const filas = 8, cols = 10;
        const colores = [PALETA.frio, PALETA.calido, PALETA.ambar, PALETA.ok];
        const cellW = w / (cols + 4), cellH = h / (filas + 2);
        for (let r = 0; r < filas; r++) {
            const dir = r % 2 === 0 ? 1 : -1;
            const avance = (Math.sin(t * 0.6 + r * 0.4) * 0.5 + 0.5);
            for (let c = 0; c < cols; c++) {
                const objetivoX = (2 + c) * cellW;
                const inicioX = dir > 0 ? -cellW * 2 : w + cellW * 2;
                const x = lerp(inicioX, objetivoX, clamp01(avance * 1.3 - c * 0.02));
                const y = (1 + r) * cellH;
                const color = colores[(r + c) % colores.length];
                ctx.globalAlpha = 0.16 + 0.1 * Math.sin(t + r + c);
                ctx.fillStyle = color;
                ctx.fillRect(x, y, cellW * 0.72, cellH * 0.5);
            }
        }
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 6) DICCIONARIO DE DATOS — nube de etiquetas (glosario) flotando.
    // ------------------------------------------------------------------
    function fondoDiccionario(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const terminos = [
            ['co2_per_capita', PALETA.frio], ['ghg_excluding_lucf', PALETA.calido],
            ['iso_code', PALETA.ok], ['year', PALETA.ambar], ['population', PALETA.morado],
            ['temperature_change', PALETA.calido], ['methane', PALETA.frio],
            ['nitrous_oxide', PALETA.ambar], ['nivel_geografico', PALETA.ok],
        ];
        // La nube de terminos se concentra en la franja derecha donde estan
        // los libros y el globo de conceptos de diccionario.jpg (foco real
        // medido: ~0.71w, 0.53h) -- antes flotaba sobre el ancho completo,
        // incluida la zona oscura izquierda donde vive el texto.
        terminos.forEach(([txt, color], i) => {
            const semilla = i * 91.7;
            const x = w * 0.5 + (Math.sin(semilla * 0.7 + t * 0.05) * 0.5 + 0.5) * w * 0.48;
            const y = ((Math.cos(semilla * 0.9) * 0.5 + 0.5) * h * 0.85 + t * (6 + i * 1.3)) % h;
            ctx.globalAlpha = 0.28;
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fillStyle = color;
            ctx.fill();
            ctx.font = '11px "IBM Plex Mono", monospace';
            ctx.fillStyle = color;
            ctx.globalAlpha = 0.22;
            ctx.textAlign = 'left';
            ctx.fillText(txt, x + 8, y + 4);
        });
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 7) CALIDAD INICIAL — barrido de escaner sobre una grilla, revelando
    // huecos (valores nulos) al pasar.
    // ------------------------------------------------------------------
    function fondoCalidad(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        // La grilla y el barrido quedan acotados a la franja donde estan
        // el microscopio y los documentos en calidad.jpg (foco real medido:
        // ~0.64w, 0.47h) -- antes barrian tambien la zona oscura izquierda,
        // escaneando "el vacio".
        const xIni = w * 0.3, xFin = w;
        const anchoZona = xFin - xIni;
        const cols = 16, filas = 12;
        const cw = anchoZona / cols, ch = h / filas;
        const barridoX = xIni + (Math.sin(t * 0.5) * 0.5 + 0.5) * anchoZona;
        for (let r = 0; r < filas; r++) {
            for (let c = 0; c < cols; c++) {
                const x = xIni + c * cw, y = r * ch;
                const dist = Math.abs((x + cw / 2) - barridoX);
                const cerca = clamp01(1 - dist / (anchoZona * 0.1));
                const esFalla = ((r * 31 + c * 17) % 23) === 0;
                ctx.globalAlpha = 0.05 + cerca * 0.18;
                ctx.fillStyle = esFalla && cerca > 0.4 ? PALETA.calido : PALETA.frio;
                ctx.fillRect(x + 1, y + 1, cw - 2, ch - 2);
            }
        }
        ctx.globalAlpha = 0.55;
        ctx.fillStyle = 'rgba(255,255,255,.9)';
        ctx.fillRect(barridoX - 1, 0, 2, h);
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 8) LIMITACIONES — niebla con grietas translucidas a la deriva.
    // ------------------------------------------------------------------
    function fondoLimitaciones(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const grietas = 5;
        for (let i = 0; i < grietas; i++) {
            const semilla = i * 53.1;
            const ox = (Math.sin(semilla) * 0.5 + 0.5) * w;
            const oy = (Math.cos(semilla * 1.3) * 0.5 + 0.5) * h;
            ctx.beginPath();
            ctx.moveTo(ox, oy);
            let x = ox, y = oy;
            for (let s = 0; s < 6; s++) {
                x += Math.sin(t * 0.1 + i + s) * 26;
                y += 22 + Math.cos(t * 0.08 + i + s) * 10;
                ctx.lineTo(x, y);
            }
            ctx.strokeStyle = 'rgba(255,180,84,' + (0.1 + 0.05 * Math.sin(t * 0.3 + i)) + ')';
            ctx.lineWidth = 1.2;
            ctx.stroke();
        }
        const niebla = ctx.createRadialGradient(w * 0.7, h * 0.4, 0, w * 0.7, h * 0.4, Math.max(w, h) * 0.6);
        niebla.addColorStop(0, 'rgba(255,255,255,.05)');
        niebla.addColorStop(1, 'transparent');
        ctx.fillStyle = niebla;
        ctx.fillRect(0, 0, w, h);
    }

    // ------------------------------------------------------------------
    // 9) RECOLECCION DE DATOS · Descripcion del conjunto — tres anillos
    // concentricos (Global / Regional / Nacional, los tres niveles reales
    // del dataset) donde van cayendo particulas que se asientan en el
    // anillo que les corresponde: la consolidacion multinivel que describe
    // esta pagina.
    // ------------------------------------------------------------------
    function fondoE2Descripcion(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.78, cy = h * 0.55;
        const radios = [0.44, 0.29, 0.15].map((f) => Math.min(w, h) * f);
        const colores = [PALETA.frio, PALETA.ambar, PALETA.calido];
        radios.forEach((r, i) => {
            ctx.beginPath();
            ctx.arc(cx, cy, r, 0, Math.PI * 2);
            ctx.strokeStyle = colores[i];
            ctx.globalAlpha = 0.22;
            ctx.lineWidth = 1.4;
            ctx.stroke();
        });
        ctx.globalAlpha = 1;
        const n = 30;
        for (let i = 0; i < n; i++) {
            const anillo = i % 3;
            const semilla = i * 17.3;
            const ang = semilla + t * (0.15 + anillo * 0.05);
            const r = radios[anillo] * (0.94 + 0.05 * Math.sin(t * 0.7 + i));
            const x = cx + Math.cos(ang) * r;
            const y = cy + Math.sin(ang) * r * 0.9;
            ctx.beginPath();
            ctx.arc(x, y, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = colores[anillo];
            ctx.globalAlpha = 0.55;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
        ctx.beginPath();
        ctx.arc(cx, cy, 4, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        ctx.fill();
    }

    // ------------------------------------------------------------------
    // 10) RECOLECCION DE DATOS · Perfilamiento — columnas verticales (una
    // por columna del dataset) con un barrido horizontal tipo "microscopio"
    // que revela la altura (cardinalidad/nulos) de cada una al pasar.
    // ------------------------------------------------------------------
    function fondoE2Perfilamiento(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cols = 12;
        const cw = w / (cols + 2);
        const barridoX = ((t * 0.16) % 1.3 - 0.15) * w;
        for (let i = 0; i < cols; i++) {
            const x = (i + 1) * cw;
            const alturaBase = 0.2 + ((i * 53) % 100) / 130;
            const dist = Math.abs(x - barridoX);
            const cerca = clamp01(1 - dist / (w * 0.12));
            const altura = h * alturaBase * (0.85 + 0.15 * cerca);
            ctx.globalAlpha = 0.14 + cerca * 0.3;
            ctx.fillStyle = i % 3 === 0 ? PALETA.frio : (i % 3 === 1 ? PALETA.ambar : PALETA.morado);
            ctx.fillRect(x - cw * 0.28, h - altura, cw * 0.56, altura);
        }
        ctx.globalAlpha = 0.5;
        ctx.fillStyle = 'rgba(255,255,255,.85)';
        ctx.fillRect(barridoX - 1, 0, 2, h);
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 11) RECOLECCION DE DATOS · Dimensiones y metricas — radar hexagonal
    // (las 6 dimensiones de calidad evaluadas) con el poligono de resultados
    // "respirando" cerca del borde, como el conjunto llega con alta calidad.
    // ------------------------------------------------------------------
    function fondoE2Dimensiones(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.8, cy = h * 0.52, r = Math.min(w, h) * 0.32;
        const ejes = 6;
        for (let anillo = 1; anillo <= 3; anillo++) {
            ctx.beginPath();
            for (let i = 0; i <= ejes; i++) {
                const ang = (i / ejes) * Math.PI * 2 - Math.PI / 2;
                const rr = r * (anillo / 3);
                const x = cx + Math.cos(ang) * rr, y = cy + Math.sin(ang) * rr * 0.92;
                i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            }
            ctx.strokeStyle = 'rgba(255,255,255,.1)';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        ctx.beginPath();
        for (let i = 0; i <= ejes; i++) {
            const ang = (i / ejes) * Math.PI * 2 - Math.PI / 2;
            const rr = r * (0.86 + 0.08 * Math.sin(t * 1.1 + i));
            const x = cx + Math.cos(ang) * rr, y = cy + Math.sin(ang) * rr * 0.92;
            i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
            ctx.fillStyle = PALETA.ok;
            ctx.globalAlpha = 1;
            ctx.beginPath(); ctx.arc(x, y, 3, 0, Math.PI * 2); ctx.fill();
            ctx.beginPath();
            const ang2 = (i / ejes) * Math.PI * 2 - Math.PI / 2;
            const rr2 = r * (0.86 + 0.08 * Math.sin(t * 1.1 + i));
            ctx.moveTo(cx + Math.cos(ang2) * rr2, cy + Math.sin(ang2) * rr2 * 0.92);
        }
        ctx.closePath();
        ctx.fillStyle = 'rgba(61,220,151,.14)';
        ctx.fill();
        ctx.strokeStyle = PALETA.ok;
        ctx.globalAlpha = 0.7;
        ctx.lineWidth = 1.6;
        ctx.stroke();
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 12) RECOLECCION DE DATOS · Problemas identificados — barrido tipo
    // radar/sonar que hace "sonar" los hallazgos del perfilamiento; el
    // tamano/brillo de cada blip sigue su severidad (alta = mas cerca).
    // ------------------------------------------------------------------
    function fondoE2Problemas(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.8, cy = h * 0.55, rMax = Math.min(w, h) * 0.46;
        for (let a = 1; a <= 3; a++) {
            ctx.beginPath();
            ctx.arc(cx, cy, rMax * a / 3, 0, Math.PI * 2);
            ctx.strokeStyle = 'rgba(255,180,84,.14)';
            ctx.lineWidth = 1;
            ctx.stroke();
        }
        const blips = [
            { ang: 0.4, rf: 0.35, sev: 1 }, { ang: 1.6, rf: 0.55, sev: 0.4 },
            { ang: 2.6, rf: 0.85, sev: 0.6 }, { ang: 3.5, rf: 0.62, sev: 0.6 },
            { ang: 4.4, rf: 0.9, sev: 0.3 }, { ang: 5.4, rf: 0.42, sev: 0.6 },
        ];
        const anguloBarrido = (t * 0.6) % (Math.PI * 2);
        ctx.save();
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.arc(cx, cy, rMax, anguloBarrido - 0.5, anguloBarrido);
        ctx.closePath();
        ctx.fillStyle = 'rgba(255,180,84,.08)';
        ctx.fill();
        ctx.restore();
        blips.forEach((b) => {
            const x = cx + Math.cos(b.ang) * rMax * b.rf;
            const y = cy + Math.sin(b.ang) * rMax * b.rf * 0.9;
            let diff = Math.abs(((anguloBarrido - b.ang) + Math.PI * 3) % (Math.PI * 2) - Math.PI);
            const recienTocado = clamp01(1 - diff / 0.5);
            const radio = 2.5 + b.sev * 3 + recienTocado * 4;
            ctx.beginPath();
            ctx.arc(x, y, radio, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.calido;
            ctx.globalAlpha = 0.35 + b.sev * 0.3 + recienTocado * 0.35;
            ctx.fill();
        });
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 13) RECOLECCION DE DATOS · Tratamiento — linea de ensamblaje: los
    // puntos entran dispersos por la izquierda y salen alineados en una
    // grilla ordenada por la derecha, pasando por "estaciones" de limpieza.
    // ------------------------------------------------------------------
    function fondoE2Tratamiento(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const estaciones = 4;
        for (let i = 1; i <= estaciones; i++) {
            const x = (w * i) / (estaciones + 1);
            ctx.strokeStyle = 'rgba(73,199,224,.14)';
            ctx.lineWidth = 1;
            ctx.beginPath(); ctx.moveTo(x, h * 0.1); ctx.lineTo(x, h * 0.9); ctx.stroke();
        }
        const n = 24;
        for (let i = 0; i < n; i++) {
            const fase = ((t * 0.09) + i / n) % 1;
            const x = fase * w;
            const filaObjetivo = i % 6;
            const yObjetivo = h * (0.2 + filaObjetivo * 0.11);
            const yCaotico = h * (0.15 + ((i * 37) % 100) / 130);
            const orden = clamp01(fase * 1.15);
            const y = lerp(yCaotico, yObjetivo, orden);
            ctx.beginPath();
            ctx.arc(x, y, 2.4, 0, Math.PI * 2);
            ctx.fillStyle = orden > 0.7 ? PALETA.ok : PALETA.frio;
            ctx.globalAlpha = 0.5;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 14) RECOLECCION DE DATOS · Comparacion antes/despues — espejo: puntos
    // dispersos a la izquierda (antes) y los mismos, ordenados en una
    // grilla, a la derecha (despues), con la linea divisoria pulsando.
    // ------------------------------------------------------------------
    function fondoE2Comparacion(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const mid = w * 0.5;
        const n = 30;
        for (let i = 0; i < n; i++) {
            const semilla = i * 29.7;
            const xa = (Math.sin(semilla) * 0.5 + 0.5) * mid * 0.82;
            const ya = (Math.cos(semilla * 1.7) * 0.5 + 0.5) * h;
            const jitterA = Math.sin(t * 1.4 + i) * 4;
            ctx.beginPath();
            ctx.arc(xa + jitterA, ya, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.calido;
            ctx.globalAlpha = 0.4;
            ctx.fill();

            const cols = 6, filas = 5;
            const c = i % cols, r = Math.floor(i / cols) % filas;
            const xb = mid * 1.18 + (c + 0.5) * (mid * 0.7 / cols);
            const yb = (r + 0.5) * (h / filas);
            ctx.beginPath();
            ctx.arc(xb, yb, 2.2, 0, Math.PI * 2);
            ctx.fillStyle = PALETA.ok;
            ctx.globalAlpha = 0.55;
            ctx.fill();
        }
        ctx.globalAlpha = 0.15 + 0.1 * Math.sin(t * 2);
        ctx.fillStyle = 'rgba(255,255,255,.9)';
        ctx.fillRect(mid - 1, 0, 2, h);
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 15) RECOLECCION DE DATOS · Graficas e indicadores — tablero de barras
    // horizontales animadas, eco directo de los graficos reales de la
    // pagina (por fuente, por indicador atipico).
    // ------------------------------------------------------------------
    function fondoE2Graficas(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const filas = 6;
        const alturaFila = h / (filas + 1);
        for (let i = 0; i < filas; i++) {
            const y = (i + 0.7) * alturaFila;
            const base = 0.25 + ((i * 41) % 100) / 160;
            const pulso = base + 0.12 * Math.sin(t * 0.8 + i * 1.3);
            const ancho = w * 0.62 * clamp01(pulso);
            ctx.globalAlpha = 0.5;
            ctx.fillStyle = i % 2 === 0 ? PALETA.frio : PALETA.ambar;
            ctx.fillRect(w * 0.3, y, ancho, alturaFila * 0.4);
            ctx.beginPath();
            ctx.arc(w * 0.3 + ancho, y + alturaFila * 0.2, 3, 0, Math.PI * 2);
            ctx.fillStyle = '#fff';
            ctx.globalAlpha = 0.7;
            ctx.fill();
        }
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 16) RECOLECCION DE DATOS · Analisis de causas — un agente (lupa)
    // revisa una carpeta y saca una hoja para inspeccionarla: la hoja sale,
    // se examina y vuelve a guardarse, en bucle. Metafora directa de
    // "investigar la causa detras de cada hallazgo".
    // ------------------------------------------------------------------
    function fondoE2Causas(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.78, cyFolder = h * 0.66;
        const fw = Math.min(w, h) * 0.36, fh = fw * 0.7;

        // Ciclo: 0-0.5 la hoja sale y se inspecciona, 0.5-1 vuelve a guardarse.
        const ciclo = (t * 0.22) % 1;
        const salida = ciclo < 0.5 ? easeInOutSine(ciclo / 0.5) : easeInOutSine(1 - (ciclo - 0.5) / 0.5);

        // Parte trasera de la carpeta (con pestana superior)
        ctx.fillStyle = 'rgba(255,180,84,.18)';
        ctx.beginPath();
        ctx.moveTo(cx - fw / 2, cyFolder - fh * 0.12);
        ctx.lineTo(cx - fw / 2 + fw * 0.2, cyFolder - fh * 0.34);
        ctx.lineTo(cx - fw / 2 + fw * 0.52, cyFolder - fh * 0.34);
        ctx.lineTo(cx - fw / 2 + fw * 0.62, cyFolder - fh * 0.12);
        ctx.lineTo(cx + fw / 2, cyFolder - fh * 0.12);
        ctx.lineTo(cx + fw / 2, cyFolder + fh * 0.55);
        ctx.lineTo(cx - fw / 2, cyFolder + fh * 0.55);
        ctx.closePath();
        ctx.fill();

        // Hoja que sale/entra (detras del frente de la carpeta)
        const hojaY = lerp(cyFolder + fh * 0.18, cyFolder - fh * 0.95, salida);
        ctx.save();
        ctx.translate(cx - fw * 0.04, hojaY);
        ctx.rotate(lerp(0, -0.07, salida));
        ctx.fillStyle = 'rgba(255,255,255,.94)';
        ctx.fillRect(-fw * 0.3, -fh * 0.4, fw * 0.6, fh * 0.56);
        ctx.strokeStyle = 'rgba(20,20,30,.28)';
        ctx.lineWidth = 2;
        for (let i = 0; i < 4; i++) {
            const ly = -fh * 0.4 + fh * 0.13 + i * fh * 0.1;
            ctx.beginPath();
            ctx.moveTo(-fw * 0.2, ly);
            ctx.lineTo(fw * (i === 3 ? 0.02 : 0.2), ly);
            ctx.stroke();
        }
        ctx.restore();

        // Frente de la carpeta (tapa la mitad inferior de la hoja cuando esta guardada)
        ctx.fillStyle = 'rgba(255,180,84,.34)';
        ctx.beginPath();
        ctx.moveTo(cx - fw / 2, cyFolder + fh * 0.55);
        ctx.lineTo(cx - fw / 2, cyFolder);
        ctx.lineTo(cx + fw / 2, cyFolder);
        ctx.lineTo(cx + fw / 2, cyFolder + fh * 0.55);
        ctx.closePath();
        ctx.fill();

        // Lupa del "agente" que inspecciona la hoja cuando ya salio lo suficiente
        if (salida > 0.3) {
            const a = clamp01((salida - 0.3) / 0.35);
            const lx = cx + fw * 0.4, ly = hojaY - fh * 0.04;
            ctx.globalAlpha = a * 0.9;
            ctx.beginPath();
            ctx.arc(lx, ly, fw * 0.14, 0, Math.PI * 2);
            ctx.strokeStyle = PALETA.frio;
            ctx.lineWidth = 3;
            ctx.stroke();
            ctx.beginPath();
            ctx.moveTo(lx + fw * 0.095, ly + fw * 0.095);
            ctx.lineTo(lx + fw * 0.21, ly + fw * 0.21);
            ctx.stroke();
            ctx.globalAlpha = 1;
        }
    }

    // ------------------------------------------------------------------
    // 17) RECOLECCION DE DATOS · Integracion y homologacion — una esfera
    // central (el dataset unico) rodeada de fragmentos curvos (las fuentes
    // heterogeneas) que cada cierto tiempo se separan bastante, se
    // intercalan entre si (cada uno a su propio ritmo) y vuelven a cerrarse
    // formando un anillo continuo alrededor de la esfera.
    // ------------------------------------------------------------------
    function fondoE2Integracion(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const cx = w * 0.76, cy = h * 0.54;
        const rEsfera = Math.min(w, h) * 0.14;

        const grad = ctx.createRadialGradient(
            cx - rEsfera * 0.35, cy - rEsfera * 0.35, rEsfera * 0.1, cx, cy, rEsfera);
        grad.addColorStop(0, 'rgba(255,255,255,.92)');
        grad.addColorStop(0.55, PALETA.frio);
        grad.addColorStop(1, 'rgba(12,40,58,.95)');
        ctx.beginPath();
        ctx.arc(cx, cy, rEsfera, 0, Math.PI * 2);
        ctx.fillStyle = grad;
        ctx.fill();

        const nFrag = 6;
        const anilloRadio = rEsfera * 1.9;
        const grosor = rEsfera * 0.4;
        const gapAng = 0.16;
        const segAng = (Math.PI * 2 / nFrag) - gapAng;

        for (let i = 0; i < nFrag; i++) {
            const faseSep = Math.sin(t * 0.5 + i * 1.3) * 0.5 + 0.5; // 0=cerrado junto a la esfera, 1=separado
            const faseIntercala = Math.sin(t * 0.28 + i * 2.4) * 0.22; // reacomodo angular independiente
            const radio = anilloRadio + faseSep * rEsfera * 1.6;
            const angBase = (i / nFrag) * Math.PI * 2 + t * 0.05 + faseIntercala;

            ctx.beginPath();
            ctx.arc(cx, cy, radio, angBase - segAng / 2, angBase + segAng / 2);
            ctx.strokeStyle = i % 2 === 0 ? PALETA.ambar : PALETA.morado;
            ctx.globalAlpha = 0.32 + 0.38 * (1 - faseSep);
            ctx.lineWidth = grosor;
            ctx.lineCap = 'round';
            ctx.stroke();
        }
        ctx.globalAlpha = 1;
    }

    // ------------------------------------------------------------------
    // 18) RECOLECCION DE DATOS · Plan de tratamiento — checklist que se
    // desplaza sola: cada accion real del plan aparece difuminada, se
    // enfoca al llegar a la linea de "chequeo" (donde se marca con un
    // check) y sigue avanzando, en bucle continuo.
    // ------------------------------------------------------------------
    function fondoE2Plan(ctx, w, h, t) {
        ctx.clearRect(0, 0, w, h);
        const items = [
            'Eliminacion de duplicados',
            'Tratamiento de valores nulos',
            'Correccion de tipos de datos',
            'Estandarizacion de fechas y textos',
            'Homologacion de categorias',
            'Validacion de rangos',
            'Tratamiento justificado de atipicos',
        ];
        const n = items.length;
        const cx = w * 0.7;
        const focoY = h * 0.5;
        const filaH = Math.min(h * 0.15, 44);
        const cicloTotal = filaH * n;
        const scrollY = (t * 0.5 * filaH) % cicloTotal;

        for (let k = 0; k < n; k++) {
            let y = focoY + (k * filaH - scrollY);
            while (y - focoY > cicloTotal / 2) y -= cicloTotal;
            while (y - focoY < -cicloTotal / 2) y += cicloTotal;

            const dist = Math.abs(y - focoY);
            const foco = clamp01(1 - dist / (filaH * 1.5));
            const desenfoque = Math.round((1 - foco) * 6);

            ctx.save();
            ctx.globalAlpha = 0.22 + foco * 0.7;
            if ('filter' in ctx) ctx.filter = 'blur(' + desenfoque + 'px)';
            ctx.font = (foco > 0.6 ? '600 ' : '400 ') + '13px "Inter", sans-serif';
            ctx.fillStyle = foco > 0.75 ? '#ffffff' : 'rgba(255,255,255,.72)';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(items[k], cx - w * 0.14, y);
            ctx.restore();

            const cxCheck = cx - w * 0.22;
            ctx.beginPath();
            ctx.arc(cxCheck, y, 6, 0, Math.PI * 2);
            ctx.strokeStyle = PALETA.ok;
            ctx.globalAlpha = 0.3 + foco * 0.5;
            ctx.lineWidth = 1.6;
            ctx.stroke();
            if (foco > 0.55) {
                ctx.globalAlpha = foco;
                ctx.beginPath();
                ctx.moveTo(cxCheck - 2.6, y);
                ctx.lineTo(cxCheck - 0.5, y + 2.6);
                ctx.lineTo(cxCheck + 3, y - 3);
                ctx.strokeStyle = PALETA.ok;
                ctx.lineWidth = 1.8;
                ctx.stroke();
            }
        }
        ctx.globalAlpha = 1;
        ctx.strokeStyle = 'rgba(61,220,151,.2)';
        ctx.lineWidth = 1;
        ctx.beginPath();
        ctx.moveTo(cx - w * 0.28, focoY);
        ctx.lineTo(cx + w * 0.02, focoY);
        ctx.stroke();
    }

    const FONDOS = {
        problema: fondoProblema,
        necesidades: fondoNecesidades,
        fuentes: fondoFuentes,
        dataset: fondoDataset,
        diccionario: fondoDiccionario,
        calidad: fondoCalidad,
        limitaciones: fondoLimitaciones,
        e2_descripcion: fondoE2Descripcion,
        e2_perfilamiento: fondoE2Perfilamiento,
        e2_dimensiones: fondoE2Dimensiones,
        e2_problemas: fondoE2Problemas,
        e2_tratamiento: fondoE2Tratamiento,
        e2_comparacion: fondoE2Comparacion,
        e2_graficas: fondoE2Graficas,
        e2_causas: fondoE2Causas,
        e2_integracion: fondoE2Integracion,
        e2_plan: fondoE2Plan,
    };

    document.addEventListener('DOMContentLoaded', () => {
        document.querySelectorAll('.page-hero[data-fondo]').forEach((hero) => {
            const clave = hero.dataset.fondo;

            if (clave === 'preguntas') {
                // Cruce (crossfade) entre las dos fotos reales -- La Nina
                // (fondo-foto-preguntas-base) y El Nino (...-cruce) -- segun
                // el progreso de scroll de toda la pagina. Es un listener
                // aparte del motor de canvas para que la opacidad se
                // actualice de inmediato al hacer scroll, incluso si el
                // usuario tiene "reduced motion" activado (ahi el canvas de
                // particulas no anima, pero el cruce de fotos si sigue
                // funcionando porque es solo una transicion de opacidad).
                // Estas capas viven FUERA de .page-hero a proposito (ver
                // preguntas.html) para que "position:fixed" no quede
                // recortado por el overflow:hidden del hero -- por eso se
                // buscan en todo el documento, no dentro de "hero".
                const cruce = document.querySelector('.fondo-foto-preguntas-cruce');
                const actualizarCruce = () => {
                    if (cruce) cruce.style.opacity = String(calcularProgresoScroll());
                };
                actualizarCruce();
                window.addEventListener('scroll', actualizarCruce, { passive: true });
                window.addEventListener('resize', actualizarCruce);

                const canvas = document.querySelector('.fondo-preguntas-fijo');
                if (!canvas) return;
                motor(canvas, (ctx, w, h, t) => fondoPreguntas(ctx, w, h, t, calcularProgresoScroll()), { fija: true });
                return;
            }

            const fn = FONDOS[clave];
            const canvas = hero.querySelector('.fondo-seccion');
            if (!fn || !canvas) return;
            motor(canvas, fn);
        });
    });
})();
