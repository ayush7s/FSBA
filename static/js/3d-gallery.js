/**
 * 3D Gallery Script
 * Creates an interactive 3D environment with rotating cards
 * Images and information will be loaded from this gallery config
 */

class Gallery3D {
    constructor() {
        this.canvas = document.getElementById('gallery-3d-canvas');
        if (!this.canvas) return;

        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.cards = [];
        this.currentIndex = 0;
        this.isScrolling = false;
        this.scrollTimeout = null;

        // Gallery items configuration
        // School facilities and highlights
        this.galleryItems = [
            {   title: "Student Courtyard Assembly",
                description: "Our students gathered in the school courtyard during sports day. A vibrant space where every child participates in building school traditions and community spirit.",
                
                category: "Campus",
                image: "/static/images/img1.jpg",
                color: 0x1b5e20
            },
            {
              title: "Teachers' Day Assembly",
                description: "A special assembly held in the school courtyard to honor our teachers. This event celebrates the dedication of our educators and the strong bond they share with their students.",
                category: "Events",
                image: "/static/images/img2.jpg",
                color: 0x2e7d32
            },
            {
                title: "Teachers' Day Celebration",
                description: "The prestigious day for every educator and student at Friends Shishu Bikash Academy. A heartfelt celebration of our teachers' dedication and the strong bond they share with their students.",
                category: "Events",
                image: "/static/images/img3.jpg",
                color: 0x43a047
            },
            {
                title: "School Community Gathering",
                description: "Teachers and students united during a special school event. These gatherings foster unity, respect, and create lasting bonds within our school family.",
                category: "Programs",
                image: "/static/images/img4.jpg",
                color: 0x558b2f
            },
            {
                title: "Patriotic Celebration",
                description: "The entire Friends Shishu Bikash Academy community celebrating together. We believe in nurturing not just academic excellence but also character and patriotic values.",
                category: "Community",
                image: "/static/images/img5.jpg",
                color: 0x7cb342
            }
        ];

        // Pre-check images availability
        console.log('🔍 Checking image availability:');
        this.galleryItems.forEach(item => {
            const img = new Image();
            img.onload = () => console.log('✓ Ready: ' + item.image);
            img.onerror = () => console.error('✗ Failed: ' + item.image);
            img.src = item.image;
        });

        this.init();
    }

    init() {
        if (!this.setupScene()) {
            console.error('Failed to initialize 3D scene');
            return;
        }
        this.createCards();
        this.setupEventListeners();
        this.animate();
    }

    setupScene() {
        // Check WebGL support
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (!gl) {
            console.error('WebGL is not supported on this browser');
            this.canvas.style.display = 'none';
            return false;
        }

        try {
            // Scene setup
            this.scene = new THREE.Scene();
            this.scene.background = new THREE.Color(0xf5f7fa);
            this.scene.fog = new THREE.Fog(0xf5f7fa, 100, 500);

            // Camera setup
            const width = this.canvas.clientWidth;
            const height = this.canvas.clientHeight;
            this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
            this.camera.position.z = 5;

            // Renderer setup
            this.renderer = new THREE.WebGLRenderer({
                canvas: this.canvas,
                antialias: true,
                alpha: true
            });
            this.renderer.setSize(width, height);
            this.renderer.setPixelRatio(window.devicePixelRatio);
            this.renderer.shadowMap.enabled = true;

            // Lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            this.scene.add(ambientLight);

            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(5, 10, 7);
            directionalLight.castShadow = true;
            directionalLight.shadow.mapSize.width = 2048;
            directionalLight.shadow.mapSize.height = 2048;
            this.scene.add(directionalLight);

            const pointLight = new THREE.PointLight(0x667eea, 0.5);
            pointLight.position.set(-5, 5, 5);
            this.scene.add(pointLight);
            
            return true;
        } catch (error) {
            console.error('Error setting up 3D scene:', error);
            return false;
        }
    }

    createCards() {
        const positions = [
            { x: -4, y: 0, z: 0 },
            { x: 0, y: 0, z: 0 },
            { x: 4, y: 0, z: 0 }
        ];

        const textureLoader = new THREE.TextureLoader();

        this.galleryItems.forEach((item, index) => {
            const geometry = new THREE.BoxGeometry(3, 3.8, 0.2);
            
            let material;
            try {
                // Try to load the image as a texture
                const texture = textureLoader.load(
                    item.image,
                    function onLoad() {
                        console.log('✓ Texture loaded: ' + item.image);
                    },
                    undefined,
                    function onError(err) {
                        console.error('✗ Failed to load texture: ' + item.image, err);
                    }
                );
                
                material = new THREE.MeshPhongMaterial({
                    map: texture,
                    emissive: 0x333333,
                    shininess: 80,
                    side: THREE.FrontSide
                });
            } catch (error) {
                // Fallback to color if texture fails
                console.warn('Using fallback color for: ' + item.image);
                material = new THREE.MeshPhongMaterial({
                    color: item.color,
                    emissive: 0x000000,
                    shininess: 100
                });
            }

            const mesh = new THREE.Mesh(geometry, material);
            
            // Position based on index (show 3 cards at a time)
            const posIndex = (index - this.currentIndex + this.galleryItems.length) % this.galleryItems.length;
            if (posIndex < 3) {
                mesh.position.copy(positions[posIndex]);
            } else {
                mesh.position.z = -100; // Hide off-screen
            }

            mesh.castShadow = true;
            mesh.receiveShadow = true;
            mesh.rotation.y = Math.random() * 0.3 - 0.15;
            
            mesh.userData = {
                item: item,
                index: index,
                targetPosition: mesh.position.clone(),
                targetRotation: mesh.rotation.clone()
            };

            this.scene.add(mesh);
            this.cards.push(mesh);
        });
    }

    updateCardPositions() {
        const positions = [
            { x: -4, y: 0, z: 0 },
            { x: 0, y: 0, z: 0 },
            { x: 4, y: 0, z: 0 }
        ];

        this.cards.forEach((card, index) => {
            const posIndex = (index - this.currentIndex + this.galleryItems.length) % this.galleryItems.length;
            
            if (posIndex < 3) {
                card.userData.targetPosition = new THREE.Vector3(
                    positions[posIndex].x,
                    positions[posIndex].y,
                    positions[posIndex].z
                );
                card.visible = true;
            } else {
                card.userData.targetPosition = new THREE.Vector3(0, 0, -100);
                card.visible = false;
            }

            // Center card (middle position) gets scale emphasis
            if (posIndex === 1) {
                card.userData.targetScale = 1.1;
                card.userData.targetOpacity = 1;
            } else {
                card.userData.targetScale = 0.9;
                card.userData.targetOpacity = 0.7;
            }
        });

        // Update info display
        this.updateInfoDisplay();
    }

    updateInfoDisplay() {
        const infoDiv = document.getElementById('gallery-info');
        const item = this.galleryItems[this.currentIndex];

        if (infoDiv && item) {
            infoDiv.innerHTML = `
                <h3>${item.title}</h3>
                <p>${item.description}</p>
                <span class="info-category">${item.category}</span>
                <p style="font-size: 12px; color: #999; margin-top: 15px;">
                    ${this.currentIndex + 1} of ${this.galleryItems.length}
                </p>
            `;
        }
    }

    setupEventListeners() {
        // Mouse wheel scrolling
        this.canvas.addEventListener('wheel', (e) => this.handleScroll(e), false);

        // Touch support
        let touchStartY = 0;
        this.canvas.addEventListener('touchstart', (e) => {
            touchStartY = e.touches[0].clientY;
        });

        this.canvas.addEventListener('touchmove', (e) => {
            const touchEndY = e.touches[0].clientY;
            const diff = touchStartY - touchEndY;
            
            if (Math.abs(diff) > 50) {
                e.preventDefault();
                this.currentIndex = (this.currentIndex + (diff > 0 ? 1 : -1) + this.galleryItems.length) % this.galleryItems.length;
                this.updateCardPositions();
                touchStartY = touchEndY;
            }
        });

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
                this.currentIndex = (this.currentIndex + 1) % this.galleryItems.length;
                this.updateCardPositions();
            } else if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
                this.currentIndex = (this.currentIndex - 1 + this.galleryItems.length) % this.galleryItems.length;
                this.updateCardPositions();
            }
        });

        // Handle window resize
        window.addEventListener('resize', () => this.onWindowResize());
    }

    handleScroll(event) {
        event.preventDefault();

        if (this.isScrolling) return;

        this.isScrolling = true;
        clearTimeout(this.scrollTimeout);

        // Scroll up = previous, scroll down = next
        if (event.deltaY > 0) {
            this.currentIndex = (this.currentIndex + 1) % this.galleryItems.length;
        } else {
            this.currentIndex = (this.currentIndex - 1 + this.galleryItems.length) % this.galleryItems.length;
        }

        this.updateCardPositions();

        // Longer timeout for smooth cube transition
        this.scrollTimeout = setTimeout(() => {
            this.isScrolling = false;
        }, 800);
    }

    animate() {
        requestAnimationFrame(() => this.animate());

        // Animate card positions and rotations
        this.cards.forEach((card) => {
            // Smooth position transition
            card.position.lerp(card.userData.targetPosition, 0.12);

            // Cube-like rotation animation (only Y-axis for card flip effect)
            const cardIndex = this.cards.indexOf(card);
            const posIndex = (cardIndex - this.currentIndex + this.galleryItems.length) % this.galleryItems.length;
            
            // Calculate target rotation for cube effect
            let targetRotY = 0;
            if (posIndex === 0) {
                targetRotY = Math.PI * 0.5; // Left card rotates 90 degrees
            } else if (posIndex === 1) {
                targetRotY = 0; // Center card faces forward
            } else if (posIndex === 2) {
                targetRotY = -Math.PI * 0.5; // Right card rotates -90 degrees
            }

            // Smooth rotation transition for cube effect
            card.rotation.y += (targetRotY - card.rotation.y) * 0.08;
            
            // Remove floating z-rotation
            card.rotation.z = 0;

            // Scale animation
            const targetScale = card.userData.targetScale || 0.9;
            card.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
        });

        // Fixed camera position (no floating)
        this.camera.position.x = 0;
        this.camera.position.y = 0;
        this.camera.position.z = 5;

        this.renderer.render(this.scene, this.camera);
    }

    onWindowResize() {
        const width = this.canvas.clientWidth;
        const height = this.canvas.clientHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height);
    }

    // Public method to add more gallery items
    addItem(title, description, category, imageUrl, color) {
        this.galleryItems.push({
            title,
            description,
            category,
            image: imageUrl,
            color: parseInt(color.replace('#', '0x'), 16)
        });
    }
}

// Initialize gallery when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Add retry logic for Three.js loading
    const initializeGallery = (retries = 0) => {
        if (typeof THREE !== 'undefined') {
            try {
                console.log('🎬 Initializing 3D Gallery...');
                const gallery = new Gallery3D();
                window.gallery3D = gallery;
                console.log('✓ 3D Gallery initialized successfully');
                console.log('📸 Loaded items:', gallery.galleryItems.length);
                gallery.galleryItems.forEach((item, i) => {
                    console.log(`  ${i + 1}. ${item.title} - ${item.image}`);
                });
            } catch (error) {
                console.error('Error initializing 3D Gallery:', error);
            }
        } else if (retries < 5) {
            // Retry if Three.js not loaded yet
            setTimeout(() => initializeGallery(retries + 1), 500);
        } else {
            console.warn('Three.js failed to load. 3D Gallery will not be available.');
        }
    };
    
    // Start initialization
    initializeGallery();
});

// Fallback initialization for late script loading
window.addEventListener('load', () => {
    if (typeof THREE !== 'undefined' && !window.gallery3D) {
        try {
            console.log('🎬 Late initialization of 3D Gallery...');
            const gallery = new Gallery3D();
            window.gallery3D = gallery;
            console.log('✓ 3D Gallery initialized on window load');
        } catch (error) {
            console.error('Error initializing 3D Gallery on window load:', error);
        }
    }
});
