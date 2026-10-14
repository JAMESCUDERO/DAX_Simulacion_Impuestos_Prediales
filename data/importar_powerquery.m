// Importa la planilla FICTICIA en Power BI (Obtener datos > Consulta en blanco > Editor avanzado).
// Nombre de la tabla en el modelo: "Planilla Predios Urbanos" (las medidas DAX dependen de ese nombre).
// Crear antes un parametro de texto "RutaDatos" con la carpeta donde esta el CSV, p. ej. C:\repos\DAX_Simulacion_Impuestos_Prediales\data\
let
    Origen = Csv.Document(
        File.Contents(RutaDatos & "planilla_predios_urbanos_FICTICIO.csv"),
        [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]
    ),
    Encabezados = Table.PromoteHeaders(Origen, [PromoteAllScalars = true]),
    // Cultura en-US: el CSV usa punto decimal (evita errores si Power BI esta en espanol)
    Tipos = Table.TransformColumnTypes(
        Encabezados,
        {
            {"Año Vigencia", Int64.Type},
            {"Area Solar", type number},
            {"Area Solar (Año Anterior)", type number},
            {"Avalúo Solar", type number},
            {"Avalúo Solar (Después Reproceso)", type number},
            {"Avalúo Solar (Año Anterior)", type number},
            {"Avalúo Construcción", type number},
            {"Avalúo Construcción (Año Anterior)", type number},
            {"Tarifa (Año Anterior)", type number},
            {"Rubro01 ImpPredial (Año Anterior)", type number},
            {"Rubro01 ImpPredial", type number},
            {"Rubro07 SolarNoEdif", type number}
        },
        "en-US"
    )
in
    Tipos
