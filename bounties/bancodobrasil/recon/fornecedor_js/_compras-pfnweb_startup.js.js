(function(PFNConfig){
	var	root = '/compras-pfnweb',
		ts = +Date.now();
	
	PFNConfig.config({
		appName: 'ComprasContratacaoModule',
		jsFiles: [
		          root+'/v1/spas/compras-contratacao-module-min.js?_t='+ts,				  
		          root+'/v1/scripts/diretivas-angular/pdf-viewer/angular-sanitize-min.js?_t='+ts,
		          root+'/v1/scripts/diretivas-angular/pdf-viewer/diretiva-pdf-viewer-min.js?_t='+ts,
				  root+'/v1/scripts/apc-compras-utils-min.js?_t='+ts,
				  root+'/v1/spas/externo/contratos-fornecedor-service-min.js?_t='+ts,
				  root+'/v1/spas/externo/autenticidade/conferencia-autenticidade-controller-min.js?_t='+ts,
				  root+'/v1/spas/externo/listar/contratos-fornecedor-listar-controller-min.js?_t='+ts,				  
				  root+'/v1/spas/interno/contratos-fornecedor-service-min.js?_t='+ts,
				  root+'/v1/spas/interno/listar/contratos-fornecedor-listar-controller-min.js?_t='+ts
				 
		]
	});
	
	PFNConfig.config({
		appName: 'ComprasContratacaoAPP',
		jsFiles: [
			root+'/v1/spas/compras-contratacao-app-min.js?_t='+ts
		]
	});
})(PFNConfig);
