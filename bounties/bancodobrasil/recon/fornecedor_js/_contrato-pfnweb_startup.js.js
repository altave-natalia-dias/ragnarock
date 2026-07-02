(function(PFNConfig){
	var	root = '/contrato-pfnweb',
		ts = +Date.now();
	PFNConfig.config({
		appName: 'ContratoModule',
		jsFiles: [
			root+'/v1/scripts/jszip-min.js?_t='+ts,
			root+'/v1/scripts/utils-min.js?_t='+ts,
			root+'/v1/scripts/filters-min.js?_t='+ts,
			root+'/v1/scripts/mask-min.js?_t='+ts,
			root+'/v1/spas/contrato-api-module-min.js?_t='+ts,
			root+'/v1/spas/contrato/contrato-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/contrato-service-min.js?_t='+ts,
			root+'/v1/spas/contrato/home/home-contrato-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/listar/contrato-listar-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/detalhar/contrato-detalhar-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/trabalhador-competencia/contrato-trabalhador-competencia-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/trabalhador-competencia/contrato-trabalhador-competencia-detalhar-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/trabalhador-competencia/contrato-trabalhador-competencia-expandir-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/documento/contrato-documento-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/envio-documento/envio-documento-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/documento/contrato-documento-factory-min.js?_t='+ts,
			root+'/v1/spas/contrato/item-contrato/contrato-item-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/ata-registro-preco-service-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/listar/ata-registro-preco-listar-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/documento/envio/ata-registro-preco-documentos-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/documento/consulta/ata-registro-preco-documentos-consulta-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/nota-fiscal/ata-registro-preco-nota-fiscal-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/detalhar/ata-registro-preco-detalhar-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/pedido-compra/listar/pedido-compra-listar-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/pedido-compra/detalhar/pedido-compra-detalhar-controller-min.js?_t='+ts,
			root+'/v1/spas/ata-registro-preco/pedido-compra/item/pedido-compra-item-listar-controller-min.js?_t='+ts,
			root+'/v1/spas/contrato/documento/fornecedor-documento-controller-min.js?_t='+ts,
		]
	});
	PFNConfig.config({
		appName: 'ContratoAPP',
		jsFiles: [
			root+'/v1/spas/contrato-api-app-min.js?_t='+ts
		]
	});
})(PFNConfig);
