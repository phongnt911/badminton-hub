/// Sân cầu lông (venues) — dùng schema v1.1, không còn cột demo.
class Venue {
  final String id;
  final String name;
  final String address;
  final String? area;
  final String? phoneNumber;
  final String? mapUrl;
  final String? imageUrl;
  final int? courtCount;
  final String? priceRange;
  final String status;

  const Venue({
    required this.id,
    required this.name,
    required this.address,
    this.area,
    this.phoneNumber,
    this.mapUrl,
    this.imageUrl,
    this.courtCount,
    this.priceRange,
    this.status = 'active',
  });

  factory Venue.fromJson(Map<String, dynamic> json) {
    return Venue(
      id: json['id']?.toString() ?? '',
      name: json['name']?.toString() ?? '',
      address: json['address']?.toString() ?? '',
      area: json['area']?.toString(),
      phoneNumber: json['phone_number']?.toString(),
      mapUrl: json['map_url']?.toString(),
      imageUrl: json['image_url']?.toString(),
      courtCount:
          json['court_count'] == null ? null : (json['court_count'] as num).toInt(),
      priceRange: json['price_range']?.toString(),
      status: json['status']?.toString() ?? 'active',
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'address': address,
        'area': area,
        'phone_number': phoneNumber,
        'map_url': mapUrl,
        'image_url': imageUrl,
        'court_count': courtCount,
        'price_range': priceRange,
        'status': status,
      };
}
