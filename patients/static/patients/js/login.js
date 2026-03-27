document.getElementById('login-form').addEventListener('submit', function(e) {
    e.preventDefault();
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            document.getElementById('lat').value = position.coords.latitude;
            document.getElementById('lng').value = position.coords.longitude;
            e.target.submit();
        }, function(error) {
            // If location access denied, submit without location
            e.target.submit();
        });
    } else {
        // Browser doesn't support geolocation
        e.target.submit();
    }
});