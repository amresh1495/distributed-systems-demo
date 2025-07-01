// Basic JavaScript to interact with the backend APIs
// This will be significantly expanded later.

document.addEventListener('DOMContentLoaded', () => {
    const productListDiv = document.querySelector('.product-list');
    const cartItemsDiv = document.querySelector('.cart-items');
    const checkoutBtn = document.getElementById('checkout-btn');
    const statusMessage = document.getElementById('status-message');

    const API_BASE_URL = '/api'; // Assuming API Gateway is at the root

    let cart = [];

    // Fetch Products
    async function fetchProducts() {
        try {
            // Adjust the endpoint when product service is fully implemented
            // For now, using a placeholder or assuming a direct endpoint if API gateway is not fully set up
            // const response = await fetch(`${API_BASE_URL}/products`); // Example: /api/products
            // if (!response.ok) throw new Error('Failed to fetch products');
            // const products = await response.json();

            // Mock products for now
            const products = [
                { id: 'prod1', name: 'Awesome Gadget', price: 29.99, stock: 10 },
                { id: 'prod2', name: 'Super Widget', price: 49.99, stock: 5 },
                { id: 'prod3', name: 'Mega Gizmo', price: 99.99, stock: 0 }, // Out of stock example
            ];

            productListDiv.innerHTML = ''; // Clear loading message
            if (products.length === 0) {
                productListDiv.innerHTML = '<p>No products available at the moment.</p>';
                return;
            }

            products.forEach(product => {
                const productDiv = document.createElement('div');
                productDiv.classList.add('product-item');
                productDiv.innerHTML = `
                    <img src="https://via.placeholder.com/150?text=${product.name.replace(/\s+/g, '+')}" alt="${product.name}">
                    <h3>${product.name}</h3>
                    <p>Price: $${product.price.toFixed(2)}</p>
                    <p>Stock: ${product.stock > 0 ? product.stock : 'Out of Stock'}</p>
                    <button class="add-to-cart-btn" data-product-id="${product.id}" ${product.stock === 0 ? 'disabled' : ''}>Add to Cart</button>
                `;
                productListDiv.appendChild(productDiv);
            });

            document.querySelectorAll('.add-to-cart-btn').forEach(button => {
                button.addEventListener('click', addToCart);
            });

        } catch (error) {
            console.error('Error fetching products:', error);
            productListDiv.innerHTML = '<p>Could not load products. Please try again later.</p>';
        }
    }

    // Add to Cart
    function addToCart(event) {
        const productId = event.target.dataset.productId;
        // In a real app, fetch product details again to ensure price/stock accuracy
        // For this mock, find from the already fetched list
        const product = { // Mock product details
            'prod1': { id: 'prod1', name: 'Awesome Gadget', price: 29.99, stock: 10 },
            'prod2': { id: 'prod2', name: 'Super Widget', price: 49.99, stock: 5 },
        }[productId];


        if (product) {
            const existingItem = cart.find(item => item.id === productId);
            if (existingItem) {
                existingItem.quantity++;
            } else {
                cart.push({ ...product, quantity: 1 });
            }
            updateCartDisplay();
        }
    }

    // Update Cart Display
    function updateCartDisplay() {
        cartItemsDiv.innerHTML = '';
        if (cart.length === 0) {
            cartItemsDiv.innerHTML = '<p>Your cart is empty.</p>';
            checkoutBtn.disabled = true;
            return;
        }

        let total = 0;
        cart.forEach(item => {
            const cartItemDiv = document.createElement('div');
            cartItemDiv.classList.add('cart-item');
            cartItemDiv.innerHTML = `
                <p>${item.name} (x${item.quantity}) - $${(item.price * item.quantity).toFixed(2)}</p>
            `;
            cartItemsDiv.appendChild(cartItemDiv);
            total += item.price * item.quantity;
        });

        const totalP = document.createElement('p');
        totalP.innerHTML = `<strong>Total: $${total.toFixed(2)}</strong>`;
        cartItemsDiv.appendChild(totalP);
        checkoutBtn.disabled = false;
    }

    // Checkout
    async function handleCheckout() {
        if (cart.length === 0) return;

        checkoutBtn.disabled = true;
        checkoutBtn.textContent = 'Processing...';
        statusMessage.textContent = 'Processing your order...';

        try {
            // This is where you'd call the order service API
            // const response = await fetch(`${API_BASE_URL}/orders`, { // Example: /api/orders
            //     method: 'POST',
            //     headers: { 'Content-Type': 'application/json' },
            //     body: JSON.stringify({ items: cart /* include user ID etc. */ })
            // });

            // if (!response.ok) {
            //     const errorData = await response.json();
            //     throw new Error(errorData.detail || 'Order placement failed');
            // }
            // const orderResult = await response.json();

            // Mock order placement
            await new Promise(resolve => setTimeout(resolve, 2000)); // Simulate network delay
            const orderResult = { orderId: `mock-${Date.now()}`, status: 'Order Placed Successfully!' };


            statusMessage.textContent = `Order ${orderResult.orderId} status: ${orderResult.status}`;
            cart = []; // Clear cart
            updateCartDisplay();

        } catch (error) {
            console.error('Checkout error:', error);
            statusMessage.textContent = `Error: ${error.message}`;
        } finally {
            checkoutBtn.disabled = false;
            checkoutBtn.textContent = 'Checkout';
        }
    }

    checkoutBtn.addEventListener('click', handleCheckout);

    // Initial load
    fetchProducts();
    updateCartDisplay();
});
