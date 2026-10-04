/* HardGo Electrical & Electronics Delivery Platform - Frontend App Controller */

let currentUser = null;
let currentRole = 'customer';
let cart = []; // [{shop_id, shop_name, product_id, shop_product_id, name, price, quantity, max_stock, est_delivery_text}]
let userLocation = { lat: 16.5062, lng: 80.6480, name: 'Benz Circle, Vijayawada' };
let currentTrackingOrderId = null;
let trackingInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeAllModals();
    });
});

async function initApp() {
    await fetchSessionUser();
    bindEvents();
    renderCurrentRoleView();
}

async function fetchSessionUser() {
    try {
        const res = await fetch('/api/auth/session');
        const data = await res.json();
        if (data.user) {
            currentUser = data.user;
            currentRole = currentUser.role;
            const n = document.getElementById('current-user-name');
            if (n) n.textContent = currentUser.name;
            const cartBtn = document.getElementById('btn-cart');
            if (cartBtn) cartBtn.style.display = currentUser.role === 'customer' ? 'flex' : 'none';
            const brand = document.querySelector('.brand-logo');
            if (brand && currentUser.role !== 'customer') brand.href = '/dashboard';
        } else { location.href = '/login'; }
    } catch (e) {
        console.error('Session error:', e);
    }
}

function bindEvents() {

    // Search bar input
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        let debounceTimer;
        searchInput.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                performSearch(e.target.value);
            }, 300);
        });
    }

    // AI Visual Search button
    const btnAiSearch = document.getElementById('btn-ai-search');
    if (btnAiSearch) {
        btnAiSearch.addEventListener('click', () => {
            openModal('modal-ai-search');
        });
    }

    // Modal close buttons: bind directly so the X always works.
    document.querySelectorAll('.btn-close-modal').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            closeAllModals();
        });
    });
    document.querySelectorAll('.modal-overlay').forEach(overlay => {
        overlay.addEventListener('click', (e) => {
            if (e.target === overlay) closeAllModals();
        });
    });

    // Cart Button
    const btnLogout = document.getElementById('btn-logout');
    if (btnLogout) btnLogout.addEventListener('click', async () => { await fetch('/api/auth/logout',{method:'POST'}); location.href='/login'; });

    const btnCart = document.getElementById('btn-cart');
    if (btnCart) {
        btnCart.addEventListener('click', () => {
            renderCartModal();
            openModal('modal-cart');
        });
    }
}

function renderCurrentRoleView() {
    // Hide all view containers
    document.querySelectorAll('.role-view-container').forEach(c => c.style.display = 'none');

    const roleContainerMap = {
        'customer': 'view-customer',
        'shop_owner': 'view-shop-owner',
        'delivery_partner': 'view-delivery-partner',
        'admin': 'view-admin'
    };

    const targetId = roleContainerMap[currentRole] || 'view-customer';
    const container = document.getElementById(targetId);
    if (container) {
        container.style.display = 'block';
    }

    // Trigger role-specific data loaders
    if (currentRole === 'customer') {
        loadCustomerCategories();
        performSearch('');
        loadCustomerOrders();
    } else if (currentRole === 'shop_owner') {
        loadShopInventory();
        loadShopOrders();
        loadShopAiDemand();
    } else if (currentRole === 'delivery_partner') {
        loadDeliveryDashboard();
    } else if (currentRole === 'admin') {
        loadAdminDashboard();
    }
}

/* ==========================================================================
   CUSTOMER MODULE LOGIC
   ========================================================================== */

async function loadCustomerCategories() {
    try {
        const res = await fetch('/api/categories');
        const data = await res.json();
        const strip = document.getElementById('category-strip');
        if (!strip) return;

        let html = `<div class="category-pill active" onclick="filterByCategory(null, this)"><i class="fas fa-th-large"></i> All Items</div>`;
        data.categories.forEach(c => {
            html += `<div class="category-pill" onclick="filterByCategory(${c.id}, this)"><i class="fas ${c.icon}"></i> ${c.name}</div>`;
        });
        strip.innerHTML = html;
    } catch (e) {
        console.error('Error loading categories:', e);
    }
}

let activeCategoryId = null;
function filterByCategory(catId, element) {
    activeCategoryId = catId;
    document.querySelectorAll('.category-pill').forEach(p => p.classList.remove('active'));
    if (element) element.classList.add('active');
    const query = document.getElementById('search-input')?.value || '';
    performSearch(query);
}

async function performSearch(query = '') {
    const grid = document.getElementById('customer-product-grid');
    if (!grid) return;

    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-secondary);"><i class="fas fa-circle-notch fa-spin fa-2x"></i><p style="margin-top:10px;">Finding nearby shop stock...</p></div>`;

    try {
        let url = `/api/search?q=${encodeURIComponent(query)}&lat=${userLocation.lat}&lng=${userLocation.lng}`;
        if (activeCategoryId) url += `&category_id=${activeCategoryId}`;

        const res = await fetch(url);
        const data = await res.json();

        if (!data.products || data.products.length === 0) {
            grid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 60px 20px; background: var(--bg-card); border-radius: var(--radius-md); border: 1px solid var(--border-color);">
                    <i class="fas fa-search-minus fa-3x" style="color: var(--text-muted); margin-bottom: 12px;"></i>
                    <h3 style="font-weight:700;">No nearby stock found</h3>
                    <p style="color: var(--text-secondary); margin-top:4px;">Try searching for "12W LED Bulb", "6A Switch", "Type-C Charger", or "Soldering Iron".</p>
                </div>
            `;
            return;
        }

        let html = '';
        data.products.forEach(p => {
            const isStockLow = p.stock <= 5;
            const stockBadgeClass = isStockLow ? 'low' : '';

            html += `
                <div class="product-card">
                    <div class="delivery-badge">${p.est_delivery_text}</div>
                    <div class="stock-badge ${stockBadgeClass}">🟢 ${p.stock} in stock</div>

                    <div class="product-img-wrapper">
                        <img src="${p.image_url}" class="product-img" alt="${p.product_name}" onerror="this.src='/static/images/products/product_1.svg'">
                    </div>

                    <div class="product-title">${p.product_name}</div>
                    <div class="shop-info-line"><span><i class="fas fa-location-dot" style="color:var(--accent-electric);"></i> Nearby verified stock • ${p.distance_km} km away</span></div>

                    <div class="product-footer">
                        <div class="price-tag">₹${p.price}</div>
                        <button class="btn-add-cart" onclick="addToCart(${p.shop_id}, '${'Nearby verified store'}', ${p.product_id}, ${p.shop_product_id}, '${p.product_name.replace(/'/g, "\\'")}', ${p.price}, ${p.stock}, '${p.est_delivery_text}')">
                            <i class="fas fa-plus"></i> Add to Cart
                        </button>
                    </div>
                </div>
            `;
        });

        grid.innerHTML = html;
        loadAiRecommendations();
    } catch (e) {
        grid.innerHTML = `<div style="grid-column: 1/-1; color: var(--accent-red); text-align: center;">Error loading products: ${e.message}</div>`;
    }
}

async function compareShopsForProduct(productId, productName) {
    try {
        const res = await fetch(`/api/products/${productId}/shops?lat=${userLocation.lat}&lng=${userLocation.lng}`);
        const data = await res.json();

        const modalBody = document.getElementById('shop-compare-modal-body');
        if (!modalBody) return;

        let html = `<h3 style="margin-bottom:12px; font-weight:800;">${productName} - Nearby Shop Comparison</h3>`;
        html += `<p style="color:var(--text-secondary); margin-bottom:16px; font-size:0.9rem;">Direct live inventory at nearby electrical shops:</p>`;

        data.available_shops.forEach(s => {
            const stockColor = s.is_in_stock ? 'var(--accent-green)' : 'var(--accent-red)';
            html += `
                <div style="background:var(--bg-main); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; margin-bottom:10px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700; font-size:1.05rem;">${s.shop_name}</div>
                        <div style="font-size:0.82rem; color:var(--text-secondary); margin-top:2px;">
                            <i class="fas fa-map-marker-alt"></i> ${s.shop_locality} (${s.distance_km} km away) &nbsp;|&nbsp; ${s.est_delivery_text}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:800; font-size:1.2rem; color:#fff;">₹${s.price}</div>
                        <div style="font-size:0.8rem; font-weight:700; color:${stockColor}; margin-top:2px;">
                            ${s.is_in_stock ? `Stock: ${s.stock} units` : 'Out of Stock'}
                        </div>
                        ${s.is_in_stock ? `
                            <button class="btn-add-cart" style="margin-top:6px; padding:4px 10px; font-size:0.75rem;" onclick="addToCart(${s.shop_id}, '${s.shop_name.replace(/'/g, "\\'")}', ${s.product_id}, ${s.shop_product_id}, '${productName.replace(/'/g, "\\'")}', ${s.price}, ${s.stock}, '${s.est_delivery_text}'); closeAllModals();">
                                Order from ${s.shop_name.split(' ')[0]}
                            </button>
                        ` : ''}
                    </div>
                </div>
            `;
        });

        modalBody.innerHTML = html;
        openModal('modal-shop-compare');
    } catch (e) {
        showToast('Comparison failed: ' + e.message, 'error');
    }
}

// Cart operations
function addToCart(shopId, shopName, productId, shopProductId, productName, price, maxStock, estDeliveryText) {
    // HardGo Rule: Orders in one cart must come from the same shop for instant direct delivery
    if (cart.length > 0 && cart[0].shop_id !== shopId) {
        if (!confirm(`Your cart contains items from '${cart[0].shop_name}'. Replace cart with items from '${shopName}'?`)) {
            return;
        }
        cart = [];
    }

    const existing = cart.find(item => item.product_id === productId);
    if (existing) {
        if (existing.quantity + 1 > maxStock) {
            showToast(`Cannot add more. Only ${maxStock} units available at ${shopName}!`, 'error');
            return;
        }
        existing.quantity += 1;
    } else {
        cart.push({
            shop_id: shopId,
            shop_name: shopName,
            product_id: productId,
            shop_product_id: shopProductId,
            name: productName,
            price: price,
            quantity: 1,
            max_stock: maxStock,
            est_delivery_text: estDeliveryText
        });
    }

    updateCartBadge();
    showToast(`Added '${productName}' to cart!`, 'success');
}

function updateCartBadge() {
    const badge = document.getElementById('cart-count-badge');
    const totalQty = cart.reduce((sum, item) => sum + item.quantity, 0);
    if (badge) {
        badge.innerText = totalQty;
        badge.style.display = totalQty > 0 ? 'flex' : 'none';
    }
}

function renderCartModal() {
    const modalBody = document.getElementById('cart-modal-body');
    if (!modalBody) return;

    if (cart.length === 0) {
        modalBody.innerHTML = `
            <div style="text-align:center; padding:40px 20px;">
                <i class="fas fa-shopping-basket fa-3x" style="color:var(--text-muted); margin-bottom:12px;"></i>
                <h4>Your Cart is Empty</h4>
                <p style="color:var(--text-secondary); margin-top:4px;">Browse nearby electrical products and add items to order!</p>
            </div>
        `;
        return;
    }

    const shopName = cart[0].shop_name;
    const estDelivery = cart[0].est_delivery_text;
    let subtotal = 0;

    let itemsHtml = '';
    cart.forEach((item, index) => {
        const itemTotal = item.price * item.quantity;
        subtotal += itemTotal;

        itemsHtml += `
            <div style="display:flex; justify-content:space-between; align-items:center; padding:10px 0; border-bottom:1px solid var(--border-color);">
                <div>
                    <div style="font-weight:700;">${item.name}</div>
                    <div style="font-size:0.8rem; color:var(--text-secondary);">₹${item.price} each</div>
                </div>
                <div style="display:flex; align-items:center; gap:8px;">
                    <button style="background:var(--bg-input); border:1px solid var(--border-color); color:#fff; width:26px; height:26px; border-radius:4px; cursor:pointer;" onclick="changeCartQty(${index}, -1)">-</button>
                    <span style="font-weight:700; width:20px; text-align:center;">${item.quantity}</span>
                    <button style="background:var(--bg-input); border:1px solid var(--border-color); color:#fff; width:26px; height:26px; border-radius:4px; cursor:pointer;" onclick="changeCartQty(${index}, 1)">+</button>
                    <span style="font-weight:800; min-width:60px; text-align:right;">₹${itemTotal}</span>
                </div>
            </div>
        `;
    });

    const deliveryFee = 20.0;
    const totalAmount = subtotal + deliveryFee;

    modalBody.innerHTML = `
        <div style="background:rgba(2, 132, 199, 0.15); border:1px solid var(--border-bright); padding:10px 14px; border-radius:var(--radius-sm); margin-bottom:16px; font-size:0.88rem;">
            <i class="fas fa-bolt" style="color:var(--accent-electric);"></i> Fulfilling from <b>${shopName}</b> (${estDelivery})
        </div>

        <div style="max-height:220px; overflow-y:auto; margin-bottom:16px;">
            ${itemsHtml}
        </div>

        <div style="border-top:1px solid var(--border-color); padding-top:12px; margin-bottom:16px;">
            <div style="display:flex; justify-content:space-between; font-size:0.9rem; color:var(--text-secondary); margin-bottom:4px;">
                <span>Item Subtotal</span><span>₹${subtotal.toFixed(2)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.9rem; color:var(--text-secondary); margin-bottom:6px;">
                <span>Local Delivery Fee</span><span>₹${deliveryFee.toFixed(2)}</span>
            </div>
            <div style="display:flex; justify-content:space-between; font-weight:800; font-size:1.2rem; color:#fff; border-top:1px solid var(--border-color); padding-top:8px;">
                <span>Total Amount</span><span style="color:var(--accent-electric);">₹${totalAmount.toFixed(2)}</span>
            </div>
        </div>

        <div style="margin-bottom:16px;">
            <label style="font-size:0.85rem; font-weight:700; color:var(--text-secondary); display:block; margin-bottom:6px;">Delivery Location</label>
            <div style="display:flex;gap:8px;margin-bottom:8px;">
                <input type="text" id="checkout-address" class="search-input" style="flex:1;background:var(--bg-main);border:1px solid var(--border-color);border-radius:var(--radius-sm);" value="${userLocation.name}" placeholder="Search area, street, landmark...">
                <button type="button" class="btn-role-switch" style="background:var(--primary);color:#fff;padding:8px 12px;" onclick="searchAndMoveCheckoutMap()"><i class="fas fa-search"></i></button>
                <button type="button" class="btn-role-switch" style="background:var(--accent-green);color:#000;padding:8px 12px;" onclick="useCurrentCheckoutLocation()"><i class="fas fa-location-crosshairs"></i> GPS</button>
            </div>
            <div id="checkout-map" class="checkout-map"></div>
            <div style="font-size:.76rem;color:var(--text-secondary);margin-top:6px;"><i class="fas fa-info-circle"></i> Drag the marker or tap the map to choose the exact delivery point.</div>
        </div>

        <div style="margin-bottom:20px;">
            <label style="font-size:0.85rem; font-weight:700; color:var(--text-secondary); display:block; margin-bottom:6px;">Payment Method</label>
            <select id="checkout-payment-method" class="search-input" style="width:100%; background:var(--bg-main); border:1px solid var(--border-color); border-radius:var(--radius-sm); color:#fff;">
                <option value="COD">Cash on Delivery (Pay at Doorstep)</option>
                <option value="UPI">Simulated UPI / Online Payment</option>
            </select>
        </div>

        <div style="display:flex; gap:8px; margin-top:8px;">
            <button type="button" class="btn-role-switch" style="flex:1; padding:12px;" onclick="closeAllModals()">
                ← Continue Shopping
            </button>
            <button type="button" class="btn-add-cart" style="flex:1; padding:12px; font-size:1rem; border-radius:var(--radius-md);" onclick="submitPlaceOrder()">
                ⚡ Place Order (${estDelivery})
            </button>
        </div>
    `;

    setTimeout(() => {
        initCheckoutMap('checkout-map', userLocation.lat, userLocation.lng, (lat, lng, name) => {
            userLocation.lat = lat; userLocation.lng = lng; userLocation.name = name;
            const address = document.getElementById('checkout-address');
            if (address && name) address.value = name;
            updateNavLocation();
        });
    }, 80);
}

function updateNavLocation() {
    const el = document.getElementById('nav-location-text');
    if (el) el.textContent = `${userLocation.name} ⚡`;
}

async function searchAndMoveCheckoutMap() {
    const q = document.getElementById('checkout-address')?.value.trim();
    if (!q) return showToast('Enter an area, street or landmark first.', 'info');
    const ok = await searchCheckoutLocation(q, (lat,lng,name) => {
        userLocation.lat=lat; userLocation.lng=lng; userLocation.name=name;
        const address=document.getElementById('checkout-address'); if(address) address.value=name;
        updateNavLocation();
    });
    showToast(ok ? 'Location selected on map.' : 'Location not found. Try a nearby landmark.', ok ? 'success' : 'error');
}

function useCurrentCheckoutLocation() {
    if (!navigator.geolocation) return showToast('GPS is not available in this browser.', 'error');
    navigator.geolocation.getCurrentPosition(async pos => {
        const lat=pos.coords.latitude, lng=pos.coords.longitude;
        userLocation.lat=lat; userLocation.lng=lng; userLocation.name=`Current location (${lat.toFixed(5)}, ${lng.toFixed(5)})`;
        const address=document.getElementById('checkout-address'); if(address) address.value=userLocation.name;
        initCheckoutMap('checkout-map',lat,lng,(a,b,name)=>{userLocation.lat=a;userLocation.lng=b;userLocation.name=name;});
        try {
            const r=await fetch(`https://nominatim.openstreetmap.org/reverse?format=jsonv2&lat=${lat}&lon=${lng}`,{headers:{'Accept':'application/json'}});
            if(r.ok){const d=await r.json();if(d.display_name){userLocation.name=d.display_name; if(address) address.value=d.display_name;}}
        } catch(e) {}
        updateNavLocation(); showToast('Current location selected.', 'success');
    }, () => showToast('Please allow location access in the browser.', 'error'), {enableHighAccuracy:true,timeout:10000});
}

function changeCartQty(index, delta) {
    if (index < 0 || index >= cart.length) return;
    const item = cart[index];
    if (delta > 0) {
        if (item.quantity + 1 > item.max_stock) {
            showToast(`Cannot exceed available stock limit (${item.max_stock})`, 'error');
            return;
        }
        item.quantity += 1;
    } else {
        item.quantity -= 1;
        if (item.quantity <= 0) {
            cart.splice(index, 1);
        }
    }
    updateCartBadge();
    renderCartModal();
}

async function submitPlaceOrder() {
    if (cart.length === 0) return;

    const address = document.getElementById('checkout-address')?.value || userLocation.name;
    const paymentMethod = document.getElementById('checkout-payment-method')?.value || 'COD';

    const orderData = {
        shop_id: cart[0].shop_id,
        items: cart.map(i => ({ product_id: i.product_id, quantity: i.quantity })),
        delivery_address: address,
        lat: userLocation.lat,
        lng: userLocation.lng,
        payment_method: paymentMethod
    };

    try {
        const res = await fetch('/api/orders/place', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(orderData)
        });

        const data = await res.json();
        if (data.success) {
            cart = [];
            updateCartBadge();
            closeAllModals();
            showToast(`Order #${data.order_number} placed successfully!`, 'success');

            // Open Live Order Tracking View
            openOrderTrackingModal(data.order_id);
            loadCustomerOrders();
        } else {
            showToast(data.message, 'error');
        }
    } catch (e) {
        showToast('Failed to place order: ' + e.message, 'error');
    }
}

async function loadCustomerOrders() {
    const container = document.getElementById('customer-orders-list');
    if (!container) return;

    try {
        const res = await fetch('/api/orders/my-orders');
        const data = await res.json();

        if (!data.orders || data.orders.length === 0) {
            container.innerHTML = `<p style="color:var(--text-muted); font-size:0.9rem;">No recent orders placed.</p>`;
            return;
        }

        let html = '';
        data.orders.forEach(o => {
            html += `
                <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px; margin-bottom:12px; display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <div style="font-weight:700;">Order #${o.order_number} <span class="status-pill status-${o.status.toLowerCase().replace(/ /g, '')}">${o.status}</span></div>
                        <div style="font-size:0.82rem; color:var(--text-secondary); margin-top:2px;">
                            Nearby verified store &nbsp;|&nbsp; Amount: ₹${o.total_amount}
                        </div>
                    </div>
                    <button class="btn-role-switch" style="background:var(--primary); color:#fff;" onclick="openOrderTrackingModal(${o.id})">
                        <i class="fas fa-map-marker-alt"></i> Track Live
                    </button>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        console.error('Error loading customer orders:', e);
    }
}

async function openOrderTrackingModal(orderId) {
    currentTrackingOrderId = orderId;
    try {
        const res = await fetch(`/api/orders/${orderId}/track`);
        const data = await res.json();
        if (!data.success) return;

        const o = data.order;
        const modalBody = document.getElementById('tracking-modal-body');
        if (!modalBody) return;

        // Visual Status Step Progress
        const statuses = ['Order Placed', 'Shop Accepted', 'Preparing', 'Ready for Pickup', 'Picked Up', 'On the Way', 'Delivered'];
        const currentIdx = statuses.indexOf(o.status);

        let stepsHtml = '<div style="display:flex; justify-content:space-between; margin-bottom:20px; position:relative;">';
        statuses.forEach((st, idx) => {
            const isDone = idx <= currentIdx;
            const isCurrent = idx === currentIdx;
            const color = isDone ? 'var(--accent-electric)' : 'var(--text-muted)';

            stepsHtml += `
                <div style="text-align:center; flex:1; position:relative; z-index:2;">
                    <div style="width:24px; height:24px; border-radius:50%; background:${isDone ? 'var(--accent-electric)' : 'var(--bg-input)'}; color:${isDone ? '#000' : '#fff'}; display:flex; align-items:center; justify-content:center; margin:0 auto 4px auto; font-size:0.7rem; font-weight:800;">
                        ${isDone ? '✓' : idx + 1}
                    </div>
                    <div style="font-size:0.65rem; color:${isDone ? '#fff' : 'var(--text-muted)'}; font-weight:${isCurrent ? '800' : '500'};">${st}</div>
                </div>
            `;
        });
        stepsHtml += '</div>';

        let itemsText = o.items.map(i => `${i.product_name} x${i.quantity}`).join(', ');

        modalBody.innerHTML = `
            <div style="margin-bottom:16px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="font-weight:800;">Order #${o.order_number}</h3>
                    <span class="status-pill status-${o.status.toLowerCase().replace(/ /g, '')}">${o.status}</span>
                </div>
                <p style="color:var(--text-secondary); font-size:0.85rem; margin-top:2px;">From <b>Nearby verified store</b> • Est. Delivery: ~${o.estimated_delivery_mins} min</p>
            </div>

            ${stepsHtml}

            <div id="tracking-map"></div>

            <div style="background:var(--bg-main); border:1px solid var(--border-color); border-radius:var(--radius-sm); padding:12px; font-size:0.88rem; margin-top:12px;">
                <div style="margin-bottom:4px;"><b>Items:</b> ${itemsText}</div>
                <div style="margin-bottom:4px;"><b>Delivery Address:</b> ${o.delivery_address}</div>
                <div><b>Total Payment (${o.payment_method}):</b> ₹${o.total_amount}</div>
            </div>
        `;

        openModal('modal-tracking');

        // Initialize Leaflet map
        setTimeout(() => {
            initTrackingMap('tracking-map', o.shop_lat, o.shop_lng, o.customer_lat, o.customer_lng);
            if (o.status === 'Picked Up' || o.status === 'On the Way') {
                startSimulatedLiveMovement(o.shop_lat, o.shop_lng, o.customer_lat, o.customer_lng);
            }
        }, 300);

    } catch (e) {
        showToast('Error tracking order: ' + e.message, 'error');
    }
}

async function loadAiRecommendations() {
    const container = document.getElementById('ai-recommendations-strip');
    if (!container) return;

    try {
        const res = await fetch('/api/ai/recommendations');
        const data = await res.json();

        let html = '';
        data.recommendations.forEach(r => {
            html += `
                <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:12px; display:flex; align-items:center; gap:12px; margin-bottom:10px;">
                    <img src="${r.image_url}" style="width:48px; height:48px; border-radius:8px; object-fit:cover;">
                    <div style="flex:1;">
                        <div style="font-weight:700; font-size:0.9rem;">${r.name}</div>
                        <div style="font-size:0.75rem; color:var(--accent-electric);">${r.reason}</div>
                    </div>
                    <div style="font-weight:800; font-size:0.95rem;">₹${r.min_price}</div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        console.error('Error loading AI recommendations:', e);
    }
}

/* ==========================================================================
   AI VISUAL SEARCH LOGIC
   ========================================================================== */

async function processAiVisualSearch(sampleName = '') {
    const resultBox = document.getElementById('ai-visual-result');
    if (resultBox) {
        resultBox.innerHTML = `<div style="text-align:center; padding:20px; color:var(--accent-electric);"><i class="fas fa-microchip fa-spin fa-2x"></i><p style="margin-top:8px;">AI Computer Vision analyzing component features...</p></div>`;
    }

    try {
        let formData = new FormData();
        const fileInput = document.getElementById('ai-file-input');

        if (fileInput && fileInput.files.length > 0) {
            formData.append('image', fileInput.files[0]);
        } else if (sampleName) {
            formData.append('sample_name', sampleName);
        } else {
            formData.append('sample_name', 'led_bulb');
        }

        const res = await fetch('/api/ai/visual-search', {
            method: 'POST',
            body: formData
        });

        const data = await res.json();

        if (resultBox) {
            let stockHtml = '';
            data.nearby_in_stock_products.forEach(p => {
                stockHtml += `
                    <div style="display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid var(--border-color);">
                        <div>
                            <div style="font-weight:700;">${p.product_name}</div>
                            <div style="font-size:0.8rem; color:var(--text-secondary);">Nearby verified stock • ${p.distance_km} km</div>
                        </div>
                        <div style="text-align:right;">
                            <div style="font-weight:800; color:#fff;">₹${p.price}</div>
                            <button class="btn-add-cart" style="padding:2px 8px; font-size:0.75rem; margin-top:2px;" onclick="addToCart(${p.shop_id}, 'Nearby verified store', ${p.product_id}, ${p.shop_product_id}, '${p.product_name.replace(/'/g, "\\'")}', ${p.price}, ${p.stock}, '${p.est_delivery_text}'); closeAllModals();">Add</button>
                        </div>
                    </div>
                `;
            });

            resultBox.innerHTML = `
                <div style="background:rgba(16, 185, 129, 0.15); border:1px solid var(--accent-green); border-radius:var(--radius-md); padding:14px; margin-top:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <h4 style="font-weight:800; color:var(--accent-green);">Match: ${data.detected_component}</h4>
                        <span style="font-size:0.8rem; font-weight:700; background:var(--accent-green); color:#000; padding:2px 8px; border-radius:10px;">${(data.confidence_score*100).toFixed(0)}% Match</span>
                    </div>
                    <p style="font-size:0.82rem; color:var(--text-secondary); margin-top:4px;">OpenCV feature descriptors analyzed. Nearby shops with stock:</p>
                    <div style="margin-top:10px;">${stockHtml}</div>
                </div>
            `;
        }
    } catch (e) {
        if (resultBox) {
            resultBox.innerHTML = `<div style="color:var(--accent-red); padding:10px;">Visual search error: ${e.message}</div>`;
        }
    }
}

/* ==========================================================================
   SHOP OWNER MODULE LOGIC
   ========================================================================== */

async function loadShopInventory() {
    const tableBody = document.getElementById('shop-inventory-tbody');
    if (!tableBody) return;

    try {
        const res = await fetch('/api/shop/inventory');
        const data = await res.json();

        let html = '';
        data.inventory.forEach(item => {
            const stockColor = item.stock <= 0 ? 'var(--accent-red)' : (item.stock <= 5 ? 'var(--accent-amber)' : 'var(--accent-green)');

            html += `
                <tr>
                    <td><b>${item.product_name}</b><br><small style="color:var(--text-secondary);">${item.category_name}</small></td>
                    <td>₹<input type="number" value="${item.price}" style="width:70px; background:var(--bg-main); border:1px solid var(--border-color); color:#fff; padding:4px; border-radius:4px;" id="price-input-${item.id}"></td>
                    <td style="color:${stockColor}; font-weight:800;">
                        <input type="number" value="${item.stock}" style="width:60px; background:var(--bg-main); border:1px solid var(--border-color); color:#fff; padding:4px; border-radius:4px;" id="stock-input-${item.id}">
                    </td>
                    <td>
                        <button class="btn-role-switch" style="background:var(--primary); color:#fff; padding:4px 10px;" onclick="saveStockUpdate(${item.id})">Save</button>
                    </td>
                </tr>
            `;
        });
        tableBody.innerHTML = html;
    } catch (e) {
        console.error('Error loading shop inventory:', e);
    }
}

async function saveStockUpdate(shopProductId) {
    const priceVal = document.getElementById(`price-input-${shopProductId}`)?.value;
    const stockVal = document.getElementById(`stock-input-${shopProductId}`)?.value;

    try {
        const res = await fetch('/api/shop/stock/update', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                shop_product_id: shopProductId,
                stock: stockVal,
                price: priceVal
            })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Inventory stock updated!', 'success');
            loadShopInventory();
        }
    } catch (e) {
        showToast('Stock update failed: ' + e.message, 'error');
    }
}

async function loadShopOrders() {
    const container = document.getElementById('shop-orders-list');
    if (!container) return;

    try {
        const res = await fetch('/api/shop/orders');
        const data = await res.json();

        if (!data.orders || data.orders.length === 0) {
            container.innerHTML = `<p style="color:var(--text-muted);">No incoming orders currently.</p>`;
            return;
        }

        let html = '';
        data.orders.forEach(o => {
            const itemsSummary = o.items.map(i => `${i.product_name} x${i.quantity}`).join(', ');

            html += `
                <div style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:var(--radius-md); padding:16px; margin-bottom:14px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                        <div>
                            <span style="font-weight:800; font-size:1.1rem;">Order #${o.order_number}</span>
                            <span class="status-pill status-${o.status.toLowerCase().replace(/ /g, '')}" style="margin-left:8px;">${o.status}</span>
                        </div>
                        <div style="font-weight:800; font-size:1.2rem; color:var(--accent-electric);">₹${o.total_amount}</div>
                    </div>

                    <div style="font-size:0.88rem; color:var(--text-secondary); margin-bottom:12px;">
                        <div><b>Customer:</b> ${o.customer_name} (${o.customer_phone})</div>
                        <div><b>Items:</b> ${itemsSummary}</div>
                        <div><b>Delivery Address:</b> ${o.delivery_address}</div>
                    </div>

                    <div style="display:flex; gap:8px;">
                        ${o.status === 'Order Placed' ? `
                            <button class="btn-role-switch" style="background:var(--accent-green); color:#000;" onclick="changeOrderStatus(${o.id}, 'Shop Accepted')">Accept Order</button>
                            <button class="btn-role-switch" style="background:var(--accent-red); color:#fff;" onclick="changeOrderStatus(${o.id}, 'Rejected')">Reject Order</button>
                        ` : ''}

                        ${o.status === 'Shop Accepted' ? `
                            <button class="btn-role-switch" style="background:var(--primary); color:#fff;" onclick="changeOrderStatus(${o.id}, 'Preparing')">Mark Preparing</button>
                        ` : ''}

                        ${o.status === 'Preparing' ? `
                            <button class="btn-role-switch" style="background:var(--accent-electric); color:#000;" onclick="changeOrderStatus(${o.id}, 'Ready for Pickup')">Ready for Pickup</button>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        console.error('Error loading shop orders:', e);
    }
}

async function changeOrderStatus(orderId, newStatus) {
    try {
        const res = await fetch(`/api/shop/orders/${orderId}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: newStatus })
        });
        const data = await res.json();
        if (data.success) {
            showToast(data.message, 'success');
            loadShopOrders();
        }
    } catch (e) {
        showToast('Order update failed: ' + e.message, 'error');
    }
}

async function loadShopAiDemand() {
    const container = document.getElementById('shop-ai-demand-container');
    if (!container) return;

    try {
        const res = await fetch('/api/ai/demand-prediction');
        const data = await res.json();

        let html = '';
        data.predictions.forEach(p => {
            const isHigh = p.stock_status === 'HIGH DEMAND RISK';
            html += `
                <div class="demand-card">
                    <div>
                        <div style="font-weight:700; font-size:1rem;">${p.product_name}</div>
                        <div style="font-size:0.82rem; color:var(--text-secondary); margin-top:2px;">
                            Stock: ${p.current_stock} units &nbsp;|&nbsp; 7-Day Projected Demand: ${p.predicted_7day_demand} units
                        </div>
                        <div style="font-size:0.78rem; color:var(--accent-electric); margin-top:4px;">${p.ai_insight}</div>
                    </div>
                    <div>
                        ${isHigh ? `<div class="demand-surge-badge">⚡ ${p.trend_percentage} Surge (Restock ${p.suggested_restock})</div>` : `<div style="color:var(--accent-green); font-weight:700; font-size:0.82rem;">Stock Adequate</div>`}
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;
    } catch (e) {
        console.error('Error loading AI demand:', e);
    }
}

/* ==========================================================================
   DELIVERY PARTNER MODULE LOGIC
   ========================================================================== */

async function loadDeliveryDashboard() {
    const container = document.getElementById('delivery-requests-list');
    if (!container) return;

    try {
        const res = await fetch('/api/delivery/requests');
        const data = await res.json();

        let html = '';

        if (data.active_deliveries && data.active_deliveries.length > 0) {
            html += `<h4 style="color:var(--accent-electric); margin-bottom:10px;">Active Ongoing Delivery</h4>`;
            data.active_deliveries.forEach((o, idx) => {
                const mapId = `delivery-map-${o.id}`;
                html += `
                    <div style="background:var(--bg-card);border:1px solid var(--accent-electric);border-radius:var(--radius-md);padding:16px;margin-bottom:16px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                            <div style="font-weight:800;font-size:1.1rem;">Order #${o.order_number}</div>
                            <span class="status-pill">${o.status}</span>
                        </div>
                        <div style="font-size:.88rem;margin:10px 0 12px;">
                            <div><b>Pickup:</b> ${o.shop_name} — ${o.shop_address}</div>
                            <div><b>Drop:</b> ${o.delivery_address}</div>
                        </div>
                        <div id="${mapId}" class="delivery-order-map"></div>
                        <div style="display:flex;gap:8px;flex-wrap:wrap;">
                            <button class="btn-role-switch" style="background:var(--primary);color:#fff;" onclick="openGoogleDirections(${o.customer_lat},${o.customer_lng})"><i class="fas fa-diamond-turn-right"></i> Navigate to Customer</button>
                            ${o.status === 'Ready for Pickup' ? `<button class="btn-role-switch" style="background:var(--primary);color:#fff;" onclick="updateDeliveryStatus(${o.id}, 'Picked Up')">Picked Up from Shop</button>` : ''}
                            ${o.status === 'Picked Up' ? `<button class="btn-role-switch" style="background:var(--accent-electric);color:#000;" onclick="updateDeliveryStatus(${o.id}, 'On the Way')">On the Way</button>` : ''}
                            ${o.status === 'On the Way' ? `<button class="btn-role-switch" style="background:var(--accent-green);color:#000;" onclick="updateDeliveryStatus(${o.id}, 'Delivered')">Mark Delivered</button>` : ''}
                        </div>
                    </div>`;
            });
        }

        html += `<h4 style="margin-bottom:10px; font-weight:700;">Available Pickup Requests Nearby</h4>`;

        if (!data.available_orders || data.available_orders.length === 0) {
            html += `<p style="color:var(--text-muted);">No new delivery requests waiting.</p>`;
        } else {
            data.available_orders.forEach(o => {
                html += `
                    <div style="background:var(--bg-card);border:1px solid var(--border-color);border-radius:var(--radius-md);padding:14px;margin-bottom:12px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;">
                            <div>
                                <div style="font-weight:700;">Order #${o.order_number} (${o.distance_km} km)</div>
                                <div style="font-size:0.82rem;color:var(--text-secondary);margin-top:2px;">Pickup: ${o.shop_name} • Earning: ₹${o.delivery_fee}</div>
                            </div>
                            <button class="btn-role-switch" style="background:var(--accent-green);color:#000;" onclick="acceptDeliveryRequest(${o.id})">Accept Delivery</button>
                        </div>
                        <div style="font-size:.8rem;color:var(--text-secondary);margin-top:8px;">Drop: ${o.delivery_address}</div>
                    </div>
                `;
            });
        }

        container.innerHTML = html;
        setTimeout(() => {
            (data.active_deliveries || []).forEach(o => initDeliveryOrderMap(`delivery-map-${o.id}`, Number(o.shop_lat), Number(o.shop_lng), Number(o.customer_lat), Number(o.customer_lng)));
        }, 100);
    } catch (e) {
        console.error('Error loading delivery dashboard:', e);
    }
}

async function acceptDeliveryRequest(orderId) {
    try {
        const res = await fetch('/api/delivery/accept', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: orderId })
        });
        const data = await res.json();
        if (data.success) {
            showToast('Delivery request accepted!', 'success');
            loadDeliveryDashboard();
        } else {
            showToast(data.message || 'Delivery request could not be accepted.', 'error');
            loadDeliveryDashboard();
        }
    } catch (e) {
        showToast('Accept failed: ' + e.message, 'error');
    }
}

async function updateDeliveryStatus(orderId, status) {
    try {
        const res = await fetch('/api/delivery/status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ order_id: orderId, status: status })
        });
        const data = await res.json();
        if (data.success) {
            showToast(`Delivery status updated to ${status}!`, 'success');
            loadDeliveryDashboard();
        } else {
            showToast(data.message || 'Status update failed.', 'error');
            loadDeliveryDashboard();
        }
    } catch (e) {
        showToast('Status update failed: ' + e.message, 'error');
    }
}

/* ==========================================================================
   ADMIN MODULE LOGIC
   ========================================================================== */

async function loadAdminDashboard() {
    try {
        const res = await fetch('/api/admin/stats');
        const data = await res.json();

        document.getElementById('admin-val-customers').innerText = data.total_customers;
        document.getElementById('admin-val-shops').innerText = data.active_shops;
        document.getElementById('admin-val-orders').innerText = data.total_orders;
        document.getElementById('admin-val-revenue').innerText = '₹' + data.total_revenue;

        const tableBody = document.getElementById('admin-orders-tbody');
        if (!tableBody) return;

        let html = '';
        data.recent_orders.forEach(o => {
            html += `
                <tr>
                    <td><b>#${o.order_number}</b></td>
                    <td>${o.customer_name}</td>
                    <td>${o.shop_name}</td>
                    <td>₹${o.total_amount}</td>
                    <td><span class="status-pill status-${o.status.toLowerCase().replace(/ /g, '')}">${o.status}</span></td>
                </tr>
            `;
        });
        tableBody.innerHTML = html;
    } catch (e) {
        console.error('Error loading admin dashboard:', e);
    }
}

/* --- Modal Helpers & Toast Notification --- */
function openModal(modalId) {
    const m = document.getElementById(modalId);
    if (m) m.classList.add('active');
}

function closeAllModals() {
    document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
}

function showToast(message, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.style.cssText = 'position:fixed; bottom:20px; right:20px; z-index:9999; display:flex; flex-direction:column; gap:10px;';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    const bg = type === 'success' ? '#10b981' : (type === 'error' ? '#ef4444' : '#0284c7');
    toast.style.cssText = `background:${bg}; color:#fff; font-weight:700; font-size:0.9rem; padding:10px 18px; border-radius:10px; box-shadow:0 8px 20px rgba(0,0,0,0.4); animation: fadeIn 0.3s ease;`;
    toast.innerText = message;

    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 3500);
}
