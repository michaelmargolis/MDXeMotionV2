using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using OpenHardwareMonitor.Hardware;
using System.Net.Sockets;
using System.Net;

namespace pc_temp_monitor
{
    public partial class Form1 : Form
    {
        Computer c = new Computer()
        {
            GPUEnabled = true,
            CPUEnabled = true
        };
        float value1, value2;
        UdpClient socket = new UdpClient(10011);
        IPEndPoint target = new IPEndPoint(IPAddress.Parse("255.255.255.255"), 10010);

        public Form1()
        {
            InitializeComponent();
        }

        private void Form1_Load(object sender, EventArgs e)
        {
           c.Open();
        }

        private void timer1_Tick(object sender, EventArgs e)
        {
            foreach (var hardware in c.Hardware)
            {
                if (hardware.HardwareType == HardwareType.GpuNvidia)
                {
                    hardware.Update();
                    foreach (var sensor in hardware.Sensors)
                        if (sensor.SensorType == SensorType.Temperature)
                        {
                            value1 = sensor.Value.GetValueOrDefault();
                        }
                }
                if (hardware.HardwareType == HardwareType.CPU)
                {
                    hardware.Update();
                    foreach (var sensor in hardware.Sensors)
                        if (sensor.SensorType == SensorType.Temperature)
                        {
                            value2 = sensor.Value.GetValueOrDefault();
                        }
                }
            }
            try
            {
                txtGPU.Text = value1.ToString();
                txtCPU.Text = value2.ToString();

                string message = "GPU=" + value1 + ",CPU=" + value2;
                byte[] toSend = Encoding.ASCII.GetBytes(message);
                socket.Send(toSend, toSend.Length, target);
            }
            catch (Exception ex)
            {
                MessageBox.Show(ex.Message);
            }
        }   
            
    }
}
