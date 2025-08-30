from __future__ import annotations

from typing import Iterable, Dict
from urllib.parse import urlparse
from pathlib import Path
import re
import time
import os
import logging
import json
from datetime import datetime


def parse_product_id_from_url(url: str) -> int | None:
    try:
        path = urlparse(url).path  # e.g., /product/69912/tomate-pera-pieza
        parts = [p for p in path.split('/') if p]
        if 'product' in parts:
            idx = parts.index('product')
            if idx + 1 < len(parts):
                return int(parts[idx + 1])
    except Exception:
        return None
    return None


class CartAutomationService:
    """Automate adding products to Mercadona cart via Playwright.

    This uses browser automation and requires 'playwright' to be installed,
    plus browsers installed via: `playwright install chromium`.
    """

    def __init__(self, *, headless: bool = True, slow_mo: int = 0, postal_code: str | None = None,
                 storage_path: str | None = None, keep_open_seconds: int = 0, keep_open_forever: bool = False) -> None:
        self.headless = headless
        self.slow_mo = slow_mo
        self.postal_code = postal_code
        self.storage_path = storage_path or "data/playwright_state.json"
        self.keep_open_seconds = keep_open_seconds
        self.keep_open_forever = keep_open_forever
        self.log = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        out_dir = Path("data")
        out_dir.mkdir(parents=True, exist_ok=True)
        logger = logging.getLogger("mercadona.cart")
        if not logger.handlers:
            logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler(str(out_dir / "automation.log"), encoding="utf-8")
            fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
            fh.setFormatter(fmt)
            logger.addHandler(fh)
        return logger

    # --- Helpers ---
    def _accept_cookies(self, page) -> None:
        """Best-effort cookie consent dismissal."""
        try:
            btn = page.get_by_role(
                "button",
                name=re.compile(r"aceptar.*cookie|aceptar todas|aceptar y cerrar|aceptar", re.I),
            )
            cnt = btn.count()
            self.log.debug(f"cookies: candidates={cnt}")
            if cnt > 0:
                try:
                    btn.first.click(timeout=4000)
                    self.log.debug("cookies: clicked accept")
                except Exception as e:
                    self.log.debug(f"cookies: click failed: {e}")
        except Exception as e:
            self.log.debug(f"cookies: not found or error: {e}")

    def _handle_cp_modal(self, page) -> None:
        """Handle postal code/store dialogs when possible."""
        if not self.postal_code:
            self.log.debug("cp: postal_code not set; skipping")
            return
        try:
            # Try common inputs inside dialogs and globally
            candidates = [
                page.get_by_placeholder(re.compile(r"c[oó]digo postal|postal", re.I)),
                page.get_by_label(re.compile(r"c[oó]digo postal|postal", re.I)),
                page.locator('input[name*="postal" i]'),
                page.locator('input[name="zipcode"]'),
                page.locator('input[name="postalCode"]'),
                page.locator('input[inputmode="numeric"]'),
                page.locator('[role="dialog"] input'),
            ]
            field = None
            for c in candidates:
                try:
                    if c and c.count() > 0:
                        field = c.first
                        break
                except Exception:
                    continue
            if field:
                try:
                    field.fill(self.postal_code, timeout=6000)
                    self.log.debug("cp: filled postal code")
                except Exception:
                    try:
                        field.type(self.postal_code, timeout=6000)
                        self.log.debug("cp: typed postal code")
                    except Exception:
                        pass
                # Confirm/continue buttons
                confirms = [
                    page.get_by_role(
                        "button",
                        name=re.compile(
                            r"confirmar|continuar|guardar|aceptar|seguir|usar|listo|continuar sin iniciar sesi[oó]n",
                            re.I,
                        ),
                    ),
                    page.locator('[role="dialog"] button'),
                ]
                for b in confirms:
                    try:
                        if b.count() > 0:
                            b.first.click(timeout=6000)
                            self.log.debug("cp: clicked confirm/continue")
                            break
                    except Exception:
                        continue
                page.wait_for_timeout(400)
        except Exception as e:
            self.log.debug(f"cp: error handling modal: {e}")

    def _close_cart_drawer(self, page) -> bool:
        """Close minicart/cart side drawer if open, to avoid blocking clicks."""
        closed = False
        try:
            # Heuristics: body class scroll--block + visible dialog containing 'Carro|Carrito|Cesta'
            is_block = False
            try:
                is_block = bool(page.evaluate("document.body.classList.contains('scroll--block')"))
            except Exception:
                pass
            drawer = page.get_by_role("dialog").filter(has_text=re.compile(r"carro|carrito|cesta", re.I))
            if (drawer.count() > 0 and drawer.first.is_visible()) or is_block:
                self.log.debug("drawer: open -> attempting to close")
                # Try close button first
                close_btns = [
                    page.get_by_role("button", name=re.compile(r"cerrar|close", re.I)),
                    page.locator('[aria-label*="cerrar" i]'),
                ]
                done = False
                for loc in close_btns:
                    try:
                        if loc.count() > 0 and loc.first.is_visible():
                            loc.first.click(timeout=2000)
                            done = True
                            break
                    except Exception:
                        continue
                if not done:
                    try:
                        page.keyboard.press("Escape")
                        done = True
                    except Exception:
                        pass
                if not done:
                    try:
                        # Click somewhere neutral (page background) to dismiss
                        page.mouse.click(10, 10)
                        done = True
                    except Exception:
                        pass
                page.wait_for_timeout(200)
                closed = True
                self.log.debug("drawer: closed (best-effort)")
        except Exception as e:
            self.log.debug(f"drawer: error while closing: {e}")
        return closed

    def _find_add_button(self, page):
        """Find a robust locator for the 'Añadir' button on product page."""
        # Accept accented and non-accented forms and common synonyms
        patterns = re.compile(r"(a(?:ñ|n)adir|agregar|afegir)(?:\s+(?:al\s+)?(carro|carrito|cesta))?|a(?:ñ|n)adir|add to cart|add", re.I)
        candidates: list[tuple[str, object]] = [
            ("role=button name=patterns", page.get_by_role("button", name=patterns)),
            ("button has_text patterns", page.locator("button").filter(has_text=patterns)),
            ("[role=button] has_text patterns", page.locator('[role="button"]').filter(has_text=patterns)),
            ("button:has(span has-text Añadir)", page.locator('button:has(span:has-text("Añadir"))')),
            ("button:has-text Añadir", page.locator('button:has-text("Añadir")')),
            ("aria-label contiene añadir", page.locator('button[aria-label*="añadir" i], [role="button"][aria-label*="añadir" i]')),
            ("aria-label contiene anadir", page.locator('button[aria-label*="anadir" i], [role="button"][aria-label*="anadir" i]')),
            ("data-testid add", page.locator('[data-testid*="add" i], [data-test*="add" i]')),
        ]
        for desc, loc in candidates:
            try:
                cnt = loc.count()
                self.log.debug(f"find_add: {desc} count={cnt}")
                if cnt > 0:
                    # Iterate first few to return a visible candidate only
                    take = min(cnt, 5)
                    for i in range(take):
                        cand = loc.nth(i)
                        try:
                            vis = cand.is_visible()
                        except Exception:
                            vis = None
                        try:
                            lbl = (cand.get_attribute("aria-label") or "").strip()
                        except Exception:
                            lbl = None
                        try:
                            txt = (cand.inner_text(timeout=500) or "").strip()
                        except Exception:
                            txt = None
                        self.log.debug(f"find_add:cand[{i}] visible={vis} aria-label={lbl!r} text={txt!r}")
                        if vis:
                            return cand
            except Exception as e:
                self.log.debug(f"find_add: {desc} error: {e}")
                continue
        return None

    def _wait_for_add_button(self, page, timeout_ms: int = 15000):
        """Wait up to timeout for the 'Añadir' button to appear/become visible."""
        deadline = time.time() + (timeout_ms / 1000.0)
        last_err = None
        did_scroll = False
        did_reload = False
        while time.time() < deadline:
            try:
                # Ensure no drawers/overlays are blocking
                try:
                    self._close_cart_drawer(page)
                except Exception:
                    pass
                btn = self._find_add_button(page)
                if btn is not None:
                    try:
                        if btn.is_visible():
                            return btn
                        else:
                            pass
                    except Exception:
                        # Do not return non-visible; keep waiting
                        pass
            except Exception as e:
                last_err = e
            # Try to trigger hydration/lazy content once by scrolling
            if not did_scroll:
                try:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(200)
                    page.evaluate("window.scrollTo(0, 0)")
                    did_scroll = True
                    self.log.debug("wait_add: performed scroll to trigger hydration")
                except Exception:
                    pass
            # If still not found by half of timeout, perform a one-time reload
            if not did_reload and (deadline - time.time()) < (timeout_ms / 2000.0):
                try:
                    page.reload(wait_until="load", timeout=15000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=8000)
                    except Exception:
                        pass
                    self._accept_cookies(page)
                    self._handle_cp_modal(page)
                    self._close_cart_drawer(page)
                    did_reload = True
                    self.log.debug("wait_add: reloaded page once")
                except Exception as e:
                    self.log.debug(f"wait_add: reload failed {e}")
            try:
                page.wait_for_timeout(250)
            except Exception:
                pass
        if last_err:
            self.log.debug(f"wait_add: last_err={last_err}")
        return None

    def _cart_count(self, page) -> int:
        try:
            candidates = [
                page.locator('[data-testid*="cart" i]'),
                page.locator('[aria-label*="carrito" i]'),
                page.locator('[class*="cart" i]'),
                page.locator('a[href*="carrito" i], a[href*="cart" i]'),
            ]
            for loc in candidates:
                try:
                    if loc.count() > 0:
                        el = loc.first
                        try:
                            txt = el.inner_text(timeout=600).strip()
                        except Exception:
                            txt = None
                        if not txt:
                            txt = (el.get_attribute("aria-label") or el.get_attribute("title") or "").strip()
                        if txt:
                            m = re.search(r'(\d+)', txt)
                            if m:
                                return int(m.group(1))
                except Exception:
                    continue
        except Exception as e:
            self.log.debug(f"cart_count: error {e}")
        return -1

    def _verify_added(self, page, prev_count: int | None = None, wait_ms: int = 3500) -> bool:
        """Check several signals that the item was added to cart (prefer count increment)."""
        deadline = time.time() + (wait_ms / 1000.0)
        toast_patterns = re.compile(r"añadid[oa]|se ha añadido|agregado", re.I)
        while time.time() < deadline:
            # 1) Cart count increased?
            try:
                curr = self._cart_count(page)
                if prev_count is not None and prev_count >= 0 and curr >= 0:
                    if curr > prev_count:
                        self.log.debug(f"verify: cart count increased {prev_count} -> {curr}")
                        return True
                elif prev_count is None and curr > 0:
                    self.log.debug(f"verify: cart count now {curr}")
                    return True
            except Exception:
                pass
            # 2) Toast/snackbar text
            try:
                toast = page.get_by_text(toast_patterns)
                if toast.count() > 0:
                    self.log.debug("verify: toast/snackbar detected")
                    return True
            except Exception:
                pass
            # 3) Mini-cart visible
            try:
                minicart = page.locator('[role="dialog" i], [class*="mini" i][class*="cart" i]')
                if minicart.count() > 0 and minicart.first.is_visible():
                    self.log.debug("verify: mini-cart visible")
                    return True
            except Exception:
                pass
            page.wait_for_timeout(250)
        self.log.debug("verify: no signal within timeout")
        return False

    def _is_in_cart_on_pdp(self, page) -> bool:
        """Detect if product page already shows the item in cart (quantity stepper).

        This avoids failing with "No se encontró botón 'Añadir'" on pages that show
        'En carro 1 ud.' and a stepper instead of an Add button.
        """
        try:
            # Common textual cues
            cues = re.compile(r"en\s+(carro|carrito|cesta)|\b\d+\s*ud\.?|unidad(?:es)?", re.I)
            block = page.get_by_text(cues)
            if block.count() > 0:
                # Ensure it's visible somewhere on PDP
                try:
                    if block.first.is_visible():
                        self.log.debug("pdp: detected 'en carro' / units text -> already in cart")
                        return True
                except Exception:
                    return True
        except Exception:
            pass
        # Heuristic: a pair of buttons around a number (stepper)
        try:
            stepper_like = page.locator('button ~ span:has-text("ud") ~ button, button:has-text("-") ~ span ~ button')
            if stepper_like.count() > 0 and stepper_like.first.is_visible():
                self.log.debug("pdp: detected stepper-like controls -> already in cart")
                return True
        except Exception:
            pass
        # Visible plus/increase control strongly indicates stepper state
        try:
            plus = page.get_by_role("button", name=re.compile(r"\+|más|mas|sumar|increase|incrementar", re.I))
            if plus.count() > 0 and plus.first.is_visible():
                self.log.debug("pdp: visible plus/increase detected -> already in cart")
                return True
        except Exception:
            pass
        return False

    def _verify_in_cart_via_page(self, page, product_id: int) -> bool:
        """Navigate to cart page and check if product id appears in DOM."""
        try:
            cart_url = "https://tienda.mercadona.es/cart"
            page.goto(cart_url, wait_until="domcontentloaded", timeout=45000)
            self._accept_cookies(page)
            self._handle_cp_modal(page)
            # Try locating by link href or data attribute
            probes = [
                page.locator(f'a[href*="/product/{product_id}/"]'),
                page.locator(f'[data-product-id="{product_id}"]'),
            ]
            for loc in probes:
                try:
                    if loc.count() > 0 and loc.first.is_visible():
                        self.log.debug(f"verify_cart: found product link/attr for {product_id}")
                        return True
                except Exception:
                    continue
            # Fallback: page HTML contains product URL path
            try:
                html = page.content()
                if f"/product/{product_id}/" in html:
                    self.log.debug(f"verify_cart: found product id in HTML for {product_id}")
                    return True
            except Exception:
                pass
        except Exception as e:
            self.log.debug(f"verify_cart: error {e}")
        return False

    def _screenshot(self, page, label: str = "shot") -> str | None:
        try:
            out_dir = Path("data/screens")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            fname = out_dir / f"{ts}_{re.sub(r'[^a-zA-Z0-9_-]', '_', label)}.png"
            page.screenshot(path=str(fname), full_page=True)
            return str(fname)
        except Exception:
            return None

    def _save_html(self, page, label: str = "page") -> str | None:
        try:
            out_dir = Path("data/screens")
            out_dir.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d-%H%M%S")
            fname = out_dir / f"{ts}_{re.sub(r'[^a-zA-Z0-9_-]', '_', label)}.html"
            html = page.content()
            with open(fname, "w", encoding="utf-8") as f:
                f.write(html)
            self.log.debug(f"debug: saved HTML -> {fname}")
            return str(fname)
        except Exception as e:
            self.log.debug(f"debug: save HTML failed: {e}")
            return None

    def _auto_select_variant(self, page) -> bool:
        """Try to select a default variant (radio/select) if the add button is disabled."""
        try:
            radios = page.locator('input[type="radio"]:not([disabled])')
            if radios.count() > 0:
                radios.first.check(timeout=3000)
                self.log.debug("variant: selected first radio")
                return True
        except Exception:
            pass
        try:
            selects = page.locator("select:not([disabled])")
            if selects.count() > 0:
                sel = selects.first
                # choose first non-disabled option that is not placeholder
                opts = sel.locator("option:not([disabled])")
                if opts.count() > 0:
                    value = opts.first.get_attribute("value") or opts.first.inner_text().strip()
                    try:
                        sel.select_option(value=value)
                    except Exception:
                        # Fallback by index
                        sel.select_option(index=0)
                    self.log.debug("variant: selected first select option")
                    return True
        except Exception:
            pass
        return False

    def _enter_first_product_from_search(self, page) -> int | None:
        """If current page is a search results page, enter the first product.

        Returns product_id if it can be inferred from the link or resulting URL; otherwise None.
        """
        try:
            # Look for anchors that lead to product detail pages
            links = page.locator('a[href*="/product/"]')
            cnt = links.count()
            self.log.debug(f"search: product links count={cnt}")
            if cnt > 0:
                first = links.first
                href = None
                try:
                    href = first.get_attribute("href")
                except Exception:
                    href = None
                try:
                    first.scroll_into_view_if_needed(timeout=3000)
                except Exception:
                    pass
                first.click(timeout=8000)
                # Wait for navigation
                try:
                    page.wait_for_load_state("domcontentloaded", timeout=15000)
                except Exception:
                    pass
                # After navigation, re-handle possible modals
                self._accept_cookies(page)
                self._handle_cp_modal(page)
                # Infer product id from href or current URL
                pid = parse_product_id_from_url(href or page.url)
                if pid is not None:
                    self.log.debug(f"search: entered product with id={pid}")
                    return pid
        except Exception as e:
            self.log.debug(f"search: enter first product failed: {e}")
        return None

    def _load_saved_samples(self) -> list[dict]:
        """Load previously captured API samples from disk (if any)."""
        try:
            path = Path("data/cart_api_samples.json")
            if path.exists():
                import json as _json
                data = _json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    self.log.debug(f"samples: loaded {len(data)} saved samples")
                    return data
        except Exception as e:
            self.log.debug(f"samples: load failed: {e}")
        return []

    def _api_add_to_cart(self, context, product_id: int, quantity: int, samples: list[dict]) -> tuple[bool, dict]:
        """Attempt to add to cart via internal API using a captured sample as template.

        Returns (ok, meta) where meta includes diagnostics of the attempt.
        """
        meta: dict = {"used": False, "reason": None}
        try:
            # Find the last suitable sample to clone
            template = None
            target_url = None
            for s in reversed(samples or []):
                try:
                    u = s.get("url")
                    if isinstance(u, str) and "/api/carts" in u:
                        body = s.get("json") if isinstance(s.get("json"), dict) else s.get("body")
                        if isinstance(body, str):
                            try:
                                body = json.loads(body)
                            except Exception:
                                body = None
                        if isinstance(body, dict):
                            template = body
                            target_url = u
                            break
                except Exception:
                    continue
            if not template or not target_url:
                meta["reason"] = "no_sample"
                return False, meta
            # Build payload from template
            payload = dict(template)
            lines = payload.get("lines") or [{}]
            if not isinstance(lines, list) or not lines:
                lines = [{}]
            line0 = dict(lines[0])
            line0["quantity"] = int(quantity)
            line0["product_id"] = str(product_id)
            line0.setdefault("version", 1)
            line0.setdefault("sources", ["+SA"])
            payload["lines"] = [line0]
            # Perform request in same browser context/session
            try:
                resp = context.request.post(
                    target_url,
                    headers={"content-type": "application/json"},
                    data=json.dumps(payload),
                )
            except Exception as e:
                meta["reason"] = f"post_error: {e}"
                return False, meta
            ok = resp and resp.status in (200, 201, 204)
            meta.update({
                "used": True,
                "url": target_url,
                "status": getattr(resp, "status", None),
                "ok": ok,
            })
            return ok, meta
        except Exception as e:
            meta["reason"] = f"unexpected: {e}"
            return False, meta

    def _clear_cart_ui(self, page) -> bool:
        """Best-effort: open cart page and click a 'Vaciar' or remove items."""
        try:
            cart_url = "https://tienda.mercadona.es/cart"
            page.goto(cart_url, wait_until="domcontentloaded", timeout=45000)
            self._accept_cookies(page)
            self._handle_cp_modal(page)
            # Try a generic 'Vaciar' button
            try:
                vaciar = page.get_by_role("button", name=re.compile(r"vaciar|vac\u00eda", re.I))
                if vaciar.count() > 0:
                    vaciar.first.click(timeout=6000)
                    # Confirm dialog if appears
                    try:
                        confirm = page.get_by_role("button", name=re.compile(r"confirmar|aceptar|vaciar", re.I))
                        if confirm.count() > 0:
                            confirm.first.click(timeout=6000)
                    except Exception:
                        pass
                    page.wait_for_timeout(800)
                    self.log.debug("cart: clicked 'Vaciar'")
                    return True
            except Exception:
                pass
            # Fallback: click all 'Eliminar' buttons if present
            try:
                removed_any = False
                for _ in range(40):  # upper bound
                    btn = page.get_by_role("button", name=re.compile(r"eliminar|quitar|suprimir", re.I))
                    if btn.count() > 0:
                        btn.first.click(timeout=4000)
                        removed_any = True
                        page.wait_for_timeout(200)
                    else:
                        break
                if removed_any:
                    self.log.debug("cart: removed items via 'Eliminar'")
                    return True
            except Exception:
                pass
        except Exception as e:
            self.log.debug(f"cart: clear failed: {e}")
        return False

    def add_by_urls(self, urls: Iterable[str], api_first: bool = False, clear_cart: bool = False) -> Dict[str, str]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright no está instalado. Ejecuta: pip install playwright && playwright install chromium"
            ) from e

        results: Dict[str, str] = {}
        details: list[dict] = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
            self.log.debug("browser: launched")
            state_path = Path(self.storage_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            context = (
                browser.new_context(locale="es-ES", storage_state=str(state_path))
                if state_path.exists() else browser.new_context(locale="es-ES")
            )
            try:
                self.log.debug(f"context: created (state_exists={state_path.exists()})")
            except Exception:
                pass
            page = context.new_page()
            self.log.debug("page: created (main)")
            # Lifecycle event hooks for diagnostics
            try:
                context.on("page", lambda pg: self.log.debug(f"context: new page -> {getattr(pg, 'url', 'n/a')}") )
            except Exception:
                pass
            try:
                page.on("popup", lambda pop: self.log.debug(f"page: popup opened -> {getattr(pop, 'url', 'n/a')}") )
            except Exception:
                pass
            try:
                page.on("close", lambda: self.log.debug("page: closed"))
            except Exception:
                pass
            # Console and request-failure diagnostics
            try:
                def _on_console(msg):
                    try:
                        t = msg.type() if callable(getattr(msg, "type", None)) else getattr(msg, "type", "?")
                    except Exception:
                        t = "?"
                    try:
                        txt = msg.text() if callable(getattr(msg, "text", None)) else getattr(msg, "text", "")
                    except Exception:
                        txt = ""
                    self.log.debug(f"console: {t} {txt}")
                page.on("console", _on_console)
            except Exception:
                pass
            try:
                def _on_req_failed(req):
                    try:
                        self.log.debug(f"net-fail: {req.method} {req.url} :: {getattr(req, 'failure', None)}")
                    except Exception:
                        pass
                page.on("requestfailed", _on_req_failed)
            except Exception:
                pass
            self.log.info(f"run: headless={self.headless} slow_mo={self.slow_mo} keep_open={self.keep_open_seconds} forever={self.keep_open_forever} urls={len(list(urls)) if hasattr(urls, '__len__') else 'n/a'}")
            # Network capture (API discovery): cart/bag write operations
            captured_samples: list[dict] = []
            saved_samples: list[dict] = self._load_saved_samples()
            def _on_response(resp):
                try:
                    url = resp.url
                    if (
                        isinstance(url, str)
                        and re.search(r"(cart|bag)", url, re.I)
                        and resp.request.method in ("POST", "PUT", "PATCH")
                    ):
                        sample: dict = {
                            "method": resp.request.method,
                            "url": url,
                            "status": resp.status,
                        }
                        # Whitelist request headers that are likely relevant
                        try:
                            req_headers = getattr(resp.request, "headers", {}) or {}
                        except Exception:
                            req_headers = {}
                        whitelist = {"content-type", "accept", "x-csrf-token", "x-xsrf-token", "x-requested-with", "authorization"}
                        sample["headers"] = {k: v for k, v in req_headers.items() if k.lower() in whitelist}
                        # Capture payload
                        body_json = None
                        try:
                            body_json = resp.request.post_data_json()
                        except Exception:
                            pass
                        if body_json is not None:
                            sample["json"] = body_json
                        else:
                            try:
                                sample["body"] = resp.request.post_data or None
                            except Exception:
                                sample["body"] = None
                        captured_samples.append(sample)
                        try:
                            self.log.debug(f"net-capture: {sample['method']} {sample['status']} {sample['url']}")
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                page.on("response", _on_response)
            except Exception:
                pass
            # Enable tracing for deeper inspection
            try:
                context.tracing.start(screenshots=True, snapshots=True, sources=False)
                self.log.debug("trace: started")
            except Exception:
                pass
            # Prepare session on homepage: cookies + CP/tienda
            try:
                page.goto("https://tienda.mercadona.es", wait_until="domcontentloaded", timeout=45000)
                self._accept_cookies(page)
                self._handle_cp_modal(page)
                self.log.debug("home: prepared cookies/CP (if any)")
            except Exception:
                self.log.debug("home: preparation failed (non-fatal)")
            # Optionally clear cart before starting
            if clear_cart:
                try:
                    ok_clear = self._clear_cart_ui(page)
                    self.log.debug(f"pre: clear_cart={ok_clear}")
                except Exception as e:
                    self.log.debug(f"pre: clear_cart error: {e}")
            for url in urls:
                detail = {"url": url, "status": "pending", "message": None, "screenshot": None, "html": None}
                # Per-URL audit trail (also mirrored to file logger)
                detail["audit"] = []
                def _audit(event: str, **kw):
                    try:
                        entry = {"t": datetime.utcnow().isoformat(timespec="milliseconds") + "Z", "event": event}
                        entry.update(kw)
                        detail["audit"].append(entry)
                        # Keep file log concise
                        self.log.debug(f"audit: {event} {kw}")
                    except Exception:
                        pass
                try:
                    self.log.info(f"url: processing {url}")
                    _audit("nav.goto", url=url)
                    page.goto(url, wait_until="load", timeout=45000)
                    try:
                        page.wait_for_load_state("networkidle", timeout=20000)
                        _audit("nav.networkidle", ok=True)
                    except Exception:
                        _audit("nav.networkidle", ok=False)
                        pass
                    _audit("nav.ready", url=page.url)
                    self._accept_cookies(page)
                    # If CP/store pops up here, handle it
                    self._handle_cp_modal(page)
                    # Ensure cart drawer is closed before interaction
                    self._close_cart_drawer(page)

                    # If URL is a search-results page, enter the first product detail
                    curr_url = page.url
                    is_search = False
                    try:
                        from urllib.parse import urlparse as _urlparse
                        is_search = ("search-results" in str(curr_url)) or (_urlparse(curr_url).path or "").startswith("/search-results")
                    except Exception:
                        is_search = "search-results" in str(curr_url)
                    pid = None
                    if is_search:
                        detail["from_search"] = True
                        first_pid = self._enter_first_product_from_search(page)
                        if first_pid is None:
                            detail["screenshot"] = self._screenshot(page, label=f"no_product_in_search")
                            detail["html"] = self._save_html(page, label="no_product_in_search")
                            raise RuntimeError("No se encontró producto en resultados")
                        pid = first_pid
                    else:
                        pid = parse_product_id_from_url(curr_url)
                    try:
                        detail["product_url"] = page.url
                    except Exception:
                        pass

                    # API-first (optional) before UI
                    if api_first and pid is not None:
                        api_ok, api_meta = self._api_add_to_cart(context, pid, 1, saved_samples + captured_samples)
                        detail["api_first"] = api_meta
                        if api_ok:
                            results[url] = "added"
                            detail["status"] = "added"
                            detail["message"] = "OK (api-first)"
                            self.log.info(f"url: added via API-first -> {url}")
                            details.append(detail)
                            continue

                    # Try to ensure the 'Añadir' button is ready before we give up
                    _audit("btn.wait_start")
                    btn = self._wait_for_add_button(page, timeout_ms=15000)
                    _audit("btn.wait_end", found=bool(btn))
                    if btn is None:
                        # If PDP already shows quantity stepper / 'En carro', treat as success
                        if self._is_in_cart_on_pdp(page):
                            _audit("pdp.already_in_cart")
                            results[url] = "added"
                            detail["status"] = "added"
                            detail["message"] = "OK (ya en carrito)"
                            # Try to capture counter state
                            try:
                                detail["counter_after"] = self._cart_count(page)
                            except Exception:
                                pass
                            self.log.info(f"url: already in cart -> {url}")
                            details.append(detail)
                            continue
                        # Try API fallback even if button missing
                        if pid is not None:
                            api_ok, api_meta = self._api_add_to_cart(context, pid, 1, saved_samples + captured_samples)
                            detail["api_fallback"] = api_meta
                            if api_ok:
                                _audit("api.fallback.used", ok=True, meta=api_meta)
                                results[url] = "added"
                                detail["status"] = "added"
                                detail["message"] = "OK (api)"
                                self.log.info(f"url: added via API (no button) -> {url}")
                                details.append(detail)
                                continue
                            else:
                                _audit("api.fallback.used", ok=False, meta=api_meta)
                        detail["screenshot"] = self._screenshot(page, label=f"no_add_btn")
                        detail["html"] = self._save_html(page, label="no_add_btn")
                        _audit("error.no_add_button", screenshot=detail["screenshot"], html=detail["html"])
                        raise RuntimeError("No se encontró botón 'Añadir'")
                    else:
                        # Guard: if already in cart (stepper present), don't click plus to avoid incrementing quantity
                        if self._is_in_cart_on_pdp(page):
                            _audit("pdp.already_in_cart_after_wait")
                            results[url] = "added"
                            detail["status"] = "added"
                            detail["message"] = "OK (ya en carrito)"
                            try:
                                detail["counter_after"] = self._cart_count(page)
                            except Exception:
                                pass
                            self.log.info(f"url: already in cart (post-wait) -> {url}")
                            details.append(detail)
                            continue

                    # Baseline cart count before clicking
                    prev_count = self._cart_count(page)
                    detail["counter_before"] = prev_count
                    added_ok = False
                    last_err: str | None = None
                    for attempt in range(1, 4):
                        try:
                            meta_btn = {
                                "visible": None,
                                "enabled": None,
                                "aria": None,
                                "text": None,
                                "bbox": None,
                            }
                            try:
                                btn.scroll_into_view_if_needed(timeout=3000)
                            except Exception:
                                pass
                            try:
                                btn.wait_for(state="visible", timeout=5000)
                            except Exception:
                                pass
                            try:
                                meta_btn["visible"] = btn.is_visible()
                            except Exception:
                                pass
                            try:
                                meta_btn["enabled"] = btn.is_enabled()
                            except Exception:
                                pass
                            try:
                                meta_btn["aria"] = (btn.get_attribute("aria-label") or "").strip()
                            except Exception:
                                pass
                            try:
                                meta_btn["text"] = (btn.inner_text(timeout=800) or "").strip()
                            except Exception:
                                pass
                            try:
                                meta_btn["bbox"] = btn.bounding_box()
                            except Exception:
                                pass
                            _audit("btn.click.attempt", attempt=attempt, **meta_btn)
                        except Exception:
                            _audit("btn.click.attempt", attempt=attempt)
                        try:
                            if not btn.is_enabled():
                                self.log.debug("btn: disabled; trying variant selection")
                                changed = self._auto_select_variant(page)
                                if changed:
                                    btn = self._find_add_button(page) or btn
                            try:
                                btn.click(timeout=15000)
                                _audit("btn.click.done", attempt=attempt)
                                # Wait for a cart write request that usually happens on add
                                net_ok = False
                                try:
                                    resp = page.wait_for_response(
                                        lambda r: (
                                            isinstance(r.url, str)
                                            and ("cart" in r.url.lower() or "bag" in r.url.lower())
                                            and r.request.method in ("POST", "PUT", "PATCH")
                                            and r.status in (200, 201, 204)
                                        ),
                                        timeout=5000,
                                    )
                                    if resp:
                                        net_ok = True
                                        self.log.debug(f"net: {resp.request.method} {resp.status} {resp.url}")
                                        try:
                                            _audit("net.cart_write", method=resp.request.method, status=resp.status, url=resp.url)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                                detail["net_ok"] = net_ok
                                # Handle potential post-click modals (e.g., continuar sin iniciar sesión)
                                self._handle_cp_modal(page)
                                # If minicart opened after add, close it to keep flow stable
                                self._close_cart_drawer(page)
                                # Verification (prefer counter increment)
                                if self._verify_added(page, prev_count=prev_count):
                                    added_ok = True
                                    # capture final counter
                                    try:
                                        detail["counter_after"] = self._cart_count(page)
                                    except Exception:
                                        pass
                                    _audit("verify.ok", prev_count=prev_count, counter_after=detail.get("counter_after"))
                                    break
                                else:
                                    last_err = "sin evidencia de añadido"
                                    page.wait_for_timeout(600)
                                    _audit("verify.retry", reason=last_err)
                            except Exception as ce:
                                last_err = str(ce)
                                # If CP dialog appeared post-click, handle and retry
                                self._handle_cp_modal(page)
                                page.wait_for_timeout(400)
                                _audit("btn.click.error", attempt=attempt, error=str(ce))
                        except Exception:
                            pass
                    if not added_ok:
                        # Try API fallback using captured sample
                        if pid is not None:
                            api_ok, api_meta = self._api_add_to_cart(context, pid, 1, saved_samples + captured_samples)
                            detail["api_fallback"] = api_meta
                            if api_ok:
                                added_ok = True
                                # Optional: verify in cart after API
                                try:
                                    detail["verified_on_cart"] = self._verify_in_cart_via_page(page, pid)
                                except Exception:
                                    pass
                                _audit("api.fallback.post_retries", ok=True, meta=api_meta)
                            else:
                                _audit("api.fallback.post_retries", ok=False, meta=api_meta)
                    if added_ok:
                        results[url] = "added"
                        detail["status"] = "added"
                        detail["message"] = "OK" if not detail.get("api_fallback", {}).get("used") else "OK (api)"
                        # Record verification on cart to increase confidence
                        try:
                            if pid is not None:
                                detail["verified_on_cart"] = self._verify_in_cart_via_page(page, pid)
                        except Exception:
                            pass
                        self.log.info(f"url: added OK -> {url}")
                        _audit("done", status="added")
                    else:
                        # As last resort, verify by navigating to cart page and searching product id
                        cart_verified = False
                        pid = parse_product_id_from_url(url)
                        if pid is not None:
                            cart_verified = self._verify_in_cart_via_page(page, pid)
                        detail["verified_on_cart"] = cart_verified
                        try:
                            detail["counter_after"] = self._cart_count(page)
                        except Exception:
                            pass
                        _audit("done", status="error", last_err=last_err, verified_on_cart=cart_verified)
                except Exception as e:  # be robust per-url
                    results[url] = f"error: {e}"  # keep message for UI
                    detail["status"] = "error"
                    detail["message"] = str(e)
                    self.log.error(f"url: error -> {url} :: {e}")
                finally:
                    try:
                        detail["nav_final_url"] = page.url
                    except Exception:
                        pass
                    details.append(detail)
            try:
                # Persist state (login, postal code, etc.)
                context.storage_state(path=str(state_path))
                self.log.debug(f"state: saved to {state_path}")
            except Exception:
                self.log.debug("state: save failed (non-fatal)")
            # Pre-stop tracing before any long waits
            try:
                trace_path = Path("data/trace.zip")
                trace_path.parent.mkdir(parents=True, exist_ok=True)
                context.tracing.stop(path=str(trace_path))
                self.log.debug(f"trace: wrote -> {trace_path}")
            except Exception:
                pass
            # Optionally keep window visible for manual checks
            added_count = sum(1 for v in results.values() if v == 'added')
            error_count = sum(1 for v in results.values() if v != 'added')
            if not self.headless:
                secs = self.keep_open_seconds
                if self.keep_open_forever or secs <= 0:
                    self.log.debug("keep-open: waiting for manual browser close (forever mode)")
                    try:
                        while True:
                            try:
                                if not browser.is_connected():
                                    break
                            except Exception:
                                break
                            time.sleep(1.0)
                    except Exception:
                        pass
                else:
                    if error_count > 0:
                        secs = max(secs, 20)
                    if secs > 0:
                        self.log.debug(f"keep-open: sleeping {secs}s (errors={error_count})")
                        time.sleep(secs)
            # Close browser unless forever mode requests leaving it to the user
            try:
                if (self.keep_open_forever or self.keep_open_seconds <= 0) and not self.headless:
                    if browser.is_connected():
                        self.log.debug("keep-open: leaving browser open (forever mode)")
                    else:
                        # Already closed by the user
                        pass
                else:
                    self.log.debug("browser: closing")
                    browser.close()
                    self.log.debug("browser: closed")
            except Exception:
                pass
        # Save machine-readable details for UI
        try:
            out = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "results": details,
                "summary": {
                    "added": sum(1 for v in results.values() if v == 'added'),
                    "errors": sum(1 for v in results.values() if v != 'added'),
                },
            }
            out_path = Path("data/last_cart_results.json")
            out_path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json
            out_path.write_text(_json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log.debug(f"debug: wrote details -> {out_path}")
        except Exception as e:
            self.log.debug(f"debug: write details failed: {e}")
        # Persist captured API samples for cart operations
        try:
            samples_path = Path("data/cart_api_samples.json")
            samples_path.parent.mkdir(parents=True, exist_ok=True)
            import json as _json
            samples_path.write_text(_json.dumps(captured_samples, ensure_ascii=False, indent=2), encoding="utf-8")
            self.log.debug(f"debug: wrote net samples -> {samples_path}")
        except Exception as e:
            self.log.debug(f"debug: write net samples failed: {e}")
        self.log.info(f"run: results -> added={sum(1 for v in results.values() if v=='added')} errors={sum(1 for v in results.values() if v!='added')}")
        return results

    def setup_session(self, keep_seconds: int | None = None) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright no está instalado. Ejecuta: pip install playwright && playwright install chromium"
            ) from e

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless, slow_mo=self.slow_mo)
            state_path = Path(self.storage_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)
            context = (
                browser.new_context(locale="es-ES", storage_state=str(state_path))
                if state_path.exists() else browser.new_context(locale="es-ES")
            )
            page = context.new_page()
            page.goto("https://tienda.mercadona.es", wait_until="load", timeout=45000)
            # Accept cookies if present
            try:
                cookie_btn = page.get_by_role("button", name=re.compile(r"Aceptar.*cookie|Aceptar todas|Aceptar y cerrar|Aceptar", re.I))
                if cookie_btn.count() > 0:
                    cookie_btn.first.click(timeout=5000)
            except Exception:
                pass
            # Try to fill postal code
            if self.postal_code:
                try:
                    candidates = [
                        lambda: page.get_by_placeholder(re.compile(r"c[oó]digo postal|postal", re.I)),
                        lambda: page.get_by_label(re.compile(r"c[oó]digo postal|postal", re.I)),
                        lambda: page.locator('input[name="zipcode"]'),
                        lambda: page.locator('input[name="postalCode"]'),
                        lambda: page.locator('input[type="tel"]'),
                        lambda: page.locator('input[aria-label*="postal" i]'),
                    ]
                    for get_loc in candidates:
                        try:
                            loc = get_loc()
                            if loc and loc.count() > 0:
                                loc.first.fill(self.postal_code, timeout=8000)
                                confirm = page.get_by_role("button", name=re.compile(r"confirmar|continuar|guardar|aceptar|seguir|usar|listo", re.I))
                                if confirm.count() > 0:
                                    confirm.first.click(timeout=8000)
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
            # Give time to login/select store manually if needed
            wait_secs = keep_seconds if keep_seconds is not None else (self.keep_open_seconds or 30)
            if not self.headless and wait_secs > 0:
                time.sleep(wait_secs)
            try:
                context.storage_state(path=str(state_path))
            except Exception:
                pass
            browser.close()
        return "ok"
