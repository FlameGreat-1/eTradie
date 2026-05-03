pub mod fallback;
pub mod geoip;
pub mod region;
pub mod router;

pub use fallback::FallbackPolicy;
pub use geoip::GeoIpLookup;
pub use region::{RegionInfo, RegionSelector};
pub use router::GeoRouter;
