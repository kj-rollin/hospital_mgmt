document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('login-form');
    if (!loginForm) return;
    
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const form = e.target;
        const latInput = document.getElementById('lat');
        const lngInput = document.getElementById('lng');
        
        // If location fields don't exist, just submit
        if (!latInput || !lngInput) {
            form.submit();
            return;
        }
        
        const GEOLOCATION_TIMEOUT = 5000;
        let timeoutId = null;
        let locationObtained = false;
        
        const submitForm = () => {
            if (timeoutId) clearTimeout(timeoutId);
            if (!form.submitted) {
                form.submit();
            }
        };
        
        if (!navigator.geolocation) {
            submitForm();
            return;
        }
        
        timeoutId = setTimeout(() => {
            if (!locationObtained) {
                console.warn('Geolocation timeout - submitting without location');
                submitForm();
            }
        }, GEOLOCATION_TIMEOUT);
        
        navigator.geolocation.getCurrentPosition(
            function(position) {
                if (position && position.coords) {
                    locationObtained = true;
                    latInput.value = position.coords.latitude;
                    lngInput.value = position.coords.longitude;
                }
                submitForm();
            },
            function(error) {
                console.debug('Geolocation failed:', error?.message || 'Unknown error');
                // Continue submission even if geolocation fails
                submitForm();
            }
        );
    });
});