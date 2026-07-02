(function(w) {
    var root = '/corporativo', ts = +Date.now();

    w.PFNConfig.config({
        appName: 'FTI.Shared.Servicos.Module',
        jsFiles: [
            root + '/v1/spas/ged/fti-ged-min.js?_t=' + ts
        ]
    });

    w.PFNConfig.config({
        appName: 'CorporativoModule',
        jsFiles: [
            root + '/v1/spas/corporativo-module-min.js?_t=' + ts,
            root + '/v1/spas/areaRegiaoGeografica/area-regiao-geografica-service-min.js?_t=' + ts
        ]
    });

    w.$corporativo_infra = {};

    if ('Worker' in w) {
        configureWorker();
    } else {
        w.console.warn('--- [Application] Worker not available');
    }

    function configureWorker() {
        w.$corporativo_infra.ged_worker = new w.Worker(root + '/ged-worker.js');
        w.$corporativo_infra.ged_worker.onmessage = function(event) {
            w.console.log('--- [Application] received from worker');
            w.console.log(event.data);
            w.$corporativo_infra.ged_worker.postMessage('Configuration complete.');
        };
    }
})(window);
