self.addEventListener("push", function(event) {
    console.log('[Service Worker] Push Received.');
    console.log('[Service Worker] event.data:' + JSON.stringify(event.data));

    if (!(self.Notification && self.Notification.permission === 'granted')) {
        return;
    }

    var data = {};
    if (event.data) {
        data = event.data.json();
    }
    var title = data.title || 'Push title';
    var body = data.body || 'Push body!';
    var icon = '/static/logo.gif';

    var options = {
        body: body,
        icon: icon
    };

    event.waitUntil(
        self.registration.pushManager.getSubscription().then(function(subscription) {
            var reg_id = subscription.endpoint.split("/").pop();
            var notificationsPath = '/notification_data?registration_id=' + reg_id;
            var headers = new Headers();
            headers.append('Accept', 'application/json');
            return fetch(notificationsPath, {headers: headers}).then(function(response) {
                if (response.status !== 200) {
                    throw new Error('The API returned an error. Status Code: ' + response.status);
                }
                return response.json().then(function(notifications) {
                    self.registration.showNotification(notifications.title, {body: notifications.message, icon: icon});
                });
            }).catch(function(err) {
                console.error('Unable to retrieve notifications.', err);
                return;
            });
        })
    );
});
