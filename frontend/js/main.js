// API Configuration
const API_BASE = 'http://localhost:5000/api';

// Mobile Navigation Toggle
document.getElementById('hamburger').addEventListener('click', function() {
    const navLinks = document.getElementById('navLinks');
    navLinks.classList.toggle('active');
    
    // Animate hamburger
    const spans = this.querySelectorAll('span');
    spans[0].style.transform = navLinks.classList.contains('active') ? 'rotate(-45deg) translate(-5px, 6px)' : '';
    spans[1].style.opacity = navLinks.classList.contains('active') ? '0' : '1';
    spans[2].style.transform = navLinks.classList.contains('active') ? 'rotate(45deg) translate(-5px, -6px)' : '';
});

// Smooth Scrolling
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

// Load Events from API
async function loadEvents() {
    const eventsGrid = document.getElementById('eventsGrid');
    const loadingSpinner = document.getElementById('eventsLoading');
    
    try {
        loadingSpinner.style.display = 'block';
        
        // Simulated event data (replace with actual API call)
        const events = [
            {
                id: 1,
                title: "Community Outreach",
                description: "Join us as we serve our local community with food and fellowship.",
                date: "2024-12-15",
                time: "10:00 AM",
                location: "Church Parking Lot"
            },
            {
                id: 2,
                title: "Christmas Eve Service",
                description: "Celebrate the birth of Christ with candlelight and carols.",
                date: "2024-12-24",
                time: "7:00 PM",
                location: "Main Sanctuary"
            },
            {
                id: 3,
                title: "Youth Winter Retreat",
                description: "A weekend of fun, fellowship, and spiritual growth for teens.",
                date: "2025-01-10",
                time: "6:00 PM",
                location: "Mountain View Camp"
            }
        ];

        // Render events
        eventsGrid.innerHTML = events.slice(0, 3).map(event => `
            <div class="event-card">
                <div class="event-image">Event Image</div>
                <div class="event-details">
                    <div class="event-date">${formatDate(event.date)} at ${event.time}</div>
                    <h3>${event.title}</h3>
                    <p>${event.description}</p>
                    <p><strong>Location:</strong> ${event.location}</p>
                    <button class="btn btn-primary" onclick="viewEventDetails(${event.id})">Learn More</button>
                </div>
            </div>
        `).join('');

    } catch (error) {
        console.error('Error loading events:', error);
        eventsGrid.innerHTML = '<p>Unable to load events. Please try again later.</p>';
    } finally {
        loadingSpinner.style.display = 'none';
    }
}

// Format date helper
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

// View event details
function viewEventDetails(eventId) {
    // This would open a modal or navigate to event details
    console.log('Viewing event:', eventId);
}

// Modal functions
function openModal(modalId) {
    document.getElementById(modalId).style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// Newsletter form submission
document.getElementById('newsletterForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('newsletter-email').value;
    const errorElement = document.getElementById('newsletter-error');
    const successElement = document.getElementById('newsletter-success');
    
    // Clear previous messages
    errorElement.textContent = '';
    successElement.textContent = '';
    
    // Validate email
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        errorElement.textContent = 'Please enter a valid email address.';
        return;
    }
    
    try {
        // Simulated API call (replace with actual API call)
        const response = await fetch(`${API_BASE}/newsletter`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ email })
        });
        
        if (response.ok) {
            successElement.textContent = 'Successfully subscribed to newsletter!';
            document.getElementById('newsletter-email').value = '';
            setTimeout(() => closeModal('newsletterModal'), 2000);
        } else {
            throw new Error('Subscription failed');
        }
    } catch (error) {
        errorElement.textContent = 'Unable to subscribe. Please try again later.';
    }
});

// Close modal when clicking outside
window.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.style.display = 'none';
    }
});

// Load service times from API
async function loadServiceTimes() {
    try {
        // Simulated API call (replace with actual API call)
        const response = await fetch(`${API_BASE}/services`);
        
        if (!response.ok) {
            throw new Error('Failed to load service times');
        }
        
        // For now, using default content
    } catch (error) {
        console.error('Error loading service times:', error);
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    loadEvents();
    loadServiceTimes();
});

// Error handling wrapper
function handleApiError(error, userMessage = 'An error occurred. Please try again later.') {
    console.error('API Error:', error);
    return userMessage;
}

// Rate limiting for form submissions
const rateLimiter = {
    submissions: {},
    
    canSubmit(formId, limitMs = 60000) {
        const now = Date.now();
        const lastSubmission = this.submissions[formId];
        
        if (!lastSubmission || now - lastSubmission > limitMs) {
            this.submissions[formId] = now;
            return true;
        }
        
        return false;
    }
};

// Lazy loading for images (placeholder for future implementation)
const imageObserver = new IntersectionObserver((entries, observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const img = entry.target;
            // Load actual image source here
            observer.unobserve(img);
        }
    });
});

// Observe all images with data-src attribute
document.querySelectorAll('img[data-src]').forEach(img => {
    imageObserver.observe(img);
});