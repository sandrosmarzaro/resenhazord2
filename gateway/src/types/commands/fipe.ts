export interface FipeModels {
  modelos: Array<{ codigo: number; nome: string }>;
}

export interface FipeYear {
  codigo: string;
  nome: string;
}

export interface FipeDetails {
  Marca: string;
  Modelo: string;
  AnoModelo: number;
  Combustivel: string;
  Valor: string;
}
