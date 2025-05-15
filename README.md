# 🎯 Distance Vector Routing Protocol Simulation

Dự án này là một mô phỏng giao thức định tuyến **Distance Vector** được xây dựng bằng Python. Mỗi router là một node trong mạng, thực hiện gửi và cập nhật các vector chi phí định tuyến giữa các router với nhau. Mô hình được xây dựng với khả năng xử lý các thay đổi mạng động, áp dụng chiến lược **Poison Reverse** để tránh vòng lặp định tuyến.

## 📖 Mô tả chi tiết

Distance Vector Routing là một thuật toán định tuyến, nơi mỗi router duy trì một bảng định tuyến riêng (distance vector), chứa thông tin chi phí ngắn nhất từ nó đến các đích khác trong mạng. Định kỳ hoặc khi phát hiện thay đổi, router sẽ gửi vector của chính nó đến các hàng xóm gần kề. Giao thức này sử dụng thuật toán *Bellman-Ford* để cập nhật bảng định tuyến dựa trên thông tin khoảng cách từ các node liền kề.

Dự án này là một phần bài tập nhóm thực hành cuối kỳ của môn học Mạng máy tính, yêu cầu sinh viên cài đặt lớp `DVrouter` kế thừa từ lớp `Router`, xử lý đầy đủ các chức năng như:
- Tự động cập nhật bảng định tuyến khi có sự thay đổi từ hàng xóm.
- Xử lý thêm và xóa liên kết động.
- Gửi vector định tuyến định kỳ.
- Áp dụng **Poison Reverse** để tránh vòng lặp định tuyến.

## 🧠 Thuật toán định tuyến – Distance Vector (Bellman-Ford)
Dự án sử dụng thuật toán Distance Vector, một phiên bản phân tán của Bellman-Ford, để tính toán đường đi ngắn nhất giữa các router.
### Nguyên lý hoạt động
- Mỗi router duy trì vector khoảng cách riêng, ghi lại chi phí tốt nhất đến mọi đích.
- Router cập nhật vector khi nhận thông tin từ hàng xóm, dựa theo công thức:
  ```
  cost_to_D = min{ cost_to_D, cost_to_neighbor + neighbor.cost_to_D }
  ```
- Khi vector thay đổi, router sẽ gửi lại vector của chính nó đến các hàng xóm.
- Định kỳ, ngay cả khi không thay đổi, router vẫn broadcast lại để đảm bảo đồng bộ.
- Các router không phát vectơ khoảng cách đã nhận đến các hàng xóm của mình. Nó chỉ phát vectơ khoảng cách của riêng mình đến các hàng xóm của mình.
- Sử dụng kỹ thuật Poison Reverse để tránh tạo vòng lặp định tuyến.
 ### Các bước thực hiện 
- *Khởi tạo*: Router khởi tạo bảng khoảng cách, khoảng cách đến chính nó bằng 0, các đích khác là vô hạn.
- *Gửi cập nhật định kỳ*: Router gửi bảng khoảng cách hiện tại đến các láng giềng theo chu kỳ heartbeat.
- *Nhận cập nhật*: Router nhận bảng khoảng cách từ các láng giềng.
- *Cập nhật bảng định tuyến*: Dựa trên bảng khoảng cách nhận được, router tính toán lại chi phí đến các đích, cập nhật bảng định tuyến nếu có đường đi tốt hơn.
- *Phát lại cập nhật*: Nếu có thay đổi bảng định tuyến, router gửi thông tin cập nhật đến các láng giềng.
- *Xử lý thay đổi liên kết*: Khi một liên kết mạng thay đổi hoặc bị mất, router cập nhật bảng và thông báo cho các láng giềng.
## 💻 Python code Implementation
### Thuộc tính
- `distance (dict[str, float])`: Là bảng khoảng cách (distance vector) của router, lưu chi phí tốt nhất đến từng đích. Ví dụ: distance[dest] = cost.
- `forwarding_table (dict[str, int])`: Bảng định tuyến, ánh xạ đích đến cổng (port) để gửi gói tin đi, ví dụ forwarding_table[dest] = port.
- `neighbors (dict[int, tuple[str, float]])`: Lưu thông tin các láng giềng kết nối trực tiếp dưới dạng {port: (endpoint, cost)}, để biết đường đi và chi phí đến từng neighbor.
- `heartbeat_time`: Khoảng thời gian định kỳ gửi cập nhật bảng khoảng cách đến các neighbor.
- `last_time`: Thời điểm lần cuối router gửi cập nhật, để quản lý gửi định kỳ.
### Phương thức
- `__init__(addr, heartbeat_time)`: Khởi tạo router với địa chỉ addr và thời gian heartbeat. Khởi tạo các bảng distance, forwarding_table, neighbors.
- `broadcast_update()`: Định kỳ hoặc khi có thay đổi, gửi bảng khoảng cách hiện tại đến tất cả neighbor. Áp dụng poison reverse cho các đích mà đường đi tốt nhất đi qua chính neighbor đó (báo chi phí vô cực).
- `handle_packet(port, packet)`: Xử lý gói tin đến từ cổng port.
  + Nếu là gói dữ liệu thông thường (traceroute), chuyển tiếp dựa trên bảng định tuyến.
  + Nếu là gói routing (bảng khoảng cách từ neighbor), cập nhật lại bảng khoảng cách và bảng định tuyến nếu phát hiện đường đi tốt hơn, sau đó phát lại cập nhật.
- `handle_new_link(port, endpoint, cost)`: Xử lý khi có liên kết mới. Cập nhật thông tin neighbor, bảng khoảng cách, bảng định tuyến nếu cần thiết và phát lại cập nhật .
- `handle_remove_link(port)`: Xử lý khi một liên kết bị ngắt. Xóa thông tin liên quan đến liên kết, cập nhật lại bảng, phát lại cập nhật nếu cần.
- `handle_time(time_ms)`: Xử lý thời gian hiện tại. Nếu đã đến thời điểm gửi heartbeat, gọi broadcast_update() để gửi bảng khoảng cách định kỳ.
- `__repr__()`: Hàm hiển thị đối tượng cho mục đích debug, giúp quan sát trạng thái router dễ dàng.


## 👥 Authors
- Đây là dự án cho bài tập lớn thực hành môn Mạng máy tính tại Trường Đại học Công nghệ - ĐHQGHN
- Dự án có đóng góp của 2 sinh viên :
  + Đỗ Quang Cường - 23021484
  + Nguyễn Xuân Dương - 23021512
