window.onload = function() {
  //<editor-fold desc="Changeable Configuration Block">

  // the following lines will be replaced by docker/configurator, when it runs in a docker-container
  window.ui = SwaggerUIBundle({
    url: "./irisfhir_swagger.json",
    dom_id: '#swagger-ui',
    deepLinking: true,
    presets: [
      SwaggerUIBundle.presets.apis,
      SwaggerUIStandalonePreset
    ],
    plugins: [
      SwaggerUIBundle.plugins.DownloadUrl
    ],
    layout: "StandaloneLayout",
    requestInterceptor: function(request) {
      request.headers["Authorization"] = "Basic " + btoa("SuperUser:SYS");
      return request;
    },
    onComplete: function() {
      window.ui.preauthorizeBasic("basicAuth", "SuperUser", "SYS");
    }
  });

  //</editor-fold>
};
