export type RiskLevel =
  | "VERY_LOW"
  | "LOW"
  | "MODERATE"
  | "HIGH"
  | "CRITICAL";

export interface User {
  id: string;
  email: string;
  full_name: string;
  phone?: string;
  role?: string;
  role_id?: string;
  district_id?: string;
  is_active: boolean;
  preferred_language: string;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface DashboardSummary {
  critical_zones: number;
  high_risk_zones: number;
  active_incidents: number;
  roads_blocked: number;
  villages_at_risk: number;
  active_alerts: number;
  total_districts: number;
  total_sensors: number;
  max_risk_score: number;
}

export interface RiskZone {
  id: string;
  name: string;
  risk_score: number;
  risk_level: RiskLevel;
  latitude?: number;
  longitude?: number;
  district_id?: string;
  district_name?: string;
  village_id?: string;
  village_name?: string;
  population: number;
  area_km2: number;
  last_update?: string;
}

export interface PredictionResponse {
  risk_score: number;
  risk_level: RiskLevel;
  confidence: number;
  factors: string[];
  factor_contributions: { factor: string; contribution: number }[];
  recommended_action: string;
  model: string;
  predicted_at: string;
}

export interface Incident {
  id: string;
  incident_type: string;
  status: string;
  severity: string;
  verification_status: string;
  description?: string;
  latitude?: number;
  longitude?: number;
  reporter_name?: string;
  district_id?: string;
  reported_at: string;
  priority_score?: number;
  priority_class?: string;
}

export interface Alert {
  id: string;
  title: string;
  message: string;
  severity: string;
  alert_type: string;
  status: string;
  risk_level?: string;
  cause?: string;
  recommended_action?: string;
  affected_villages: string[];
  affected_roads: string[];
  district_id?: string;
  latitude?: number;
  longitude?: number;
  triggered_at: string;
  acknowledged_at?: string;
}

export interface Road {
  id: string;
  name: string;
  road_type: string;
  status: string;
  population_served: number;
  alternative_route: boolean;
  priority_score: number;
  latitude?: number;
  longitude?: number;
}

export interface Sensor {
  id: string;
  name: string;
  sensor_type: string;
  status: string;
  latitude?: number;
  longitude?: number;
  district_id?: string;
  district_name?: string;
  last_reading_at?: string;
}

export interface Report {
  id: string;
  report_type: string;
  severity: string;
  description?: string;
  latitude?: number;
  longitude?: number;
  reporter_name?: string;
  incident_id?: string;
  client_id?: string;
  sync_status: string;
  reported_at: string;
  media: any[];
}

export interface HealthReport {
  status: string;
  api: string;
  database: string;
  ml_model: string;
  weather_provider: string;
  satellite_provider: string;
  notification_provider: string;
  environment: string;
  components: Record<string, { status: string; detail?: string }>;
}
