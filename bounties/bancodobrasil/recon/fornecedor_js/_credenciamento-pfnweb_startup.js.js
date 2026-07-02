(function (PFNConfig) {
	
	let root = '/credenciamento-pfnweb',
		ts = + Date.now();

	PFNConfig.config({
		appName: 'QGD_CREDENCIAMENTO_MODULE',
		jsFiles: [

			root + '/v1/spas/main-module.js?_t=' + ts,

			root + '/v1/spas/viabilidade/consultar/consultar-viabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/viabilidade/consultar/consultar-viabilidade-service.js?_t=' + ts,

			root + '/v1/spas/viabilidade/registrar/registrar-viabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/viabilidade/registrar/registrar-viabilidade-service.js?_t=' + ts,

			root + '/v1/spas/viabilidade/detalhar/detalhar-viabilidade-controller.js?_t=' + ts,
			root + '/v1/spas/viabilidade/detalhar/detalhar-viabilidade-service.js?_t=' + ts,

			root + '/v1/spas/viabilidade/consultar-registradas/consultar-viabilidades-registradas-controller.js?_t=' + ts,
			root + '/v1/spas/viabilidade/consultar-registradas/consultar-viabilidades-registradas-service.js?_t=' + ts,
			
			root + '/v1/spas/componentes/menu/menu-controller.js?_t=' + ts
			
		]
	});

	PFNConfig.config({
		appName: 'QGD_CREDENCIAMENTO_APP',
		jsFiles: [
			root + '/v1/spas/main-app.js?_t=' + ts
		]
	});

})(PFNConfig);
