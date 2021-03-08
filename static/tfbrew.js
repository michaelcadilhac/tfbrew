var chartColors = {
	red: 'rgb(255, 99, 132)',
	orange: 'rgb(255, 159, 64)',
	yellow: 'rgb(255, 205, 86)',
	green: 'rgb(75, 192, 192)',
	blue: 'rgb(54, 162, 235)',
	purple: 'rgb(153, 102, 255)',
        grey: 'rgb(201, 203, 207)',
        white: 'rgb(255,255,255)'
};

var plotComp = {
    template: `
    <canvas ref="plot" width="400" height="400"></canvas>
    `,
    props: ['href'],
    data: function() {
        return {
            ctx: null,
            chart: null
        }
    },
    methods: {
        newData: function(datapoint) {
            this.chart.data.labels.push(moment(datapoint.when))
            this.chart.data.datasets[0].data.push(datapoint.temperature)
            this.chart.data.datasets[1].data.push(datapoint.power)
            this.chart.data.datasets[2].data.push(datapoint.setpoint)
            if (datapoint.gravity != undefined)
                this.chart.data.datasets[3].data.push(datapoint.gravity)
            this.chart.update()
        }
    },
    mounted: function() {
        this.ctx = this.$refs.plot.getContext('2d')
        this.chart = new Chart(this.ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Temperature',
                    fill: false,
                    backgroundColor: chartColors.red,
					borderColor: chartColors.red,
                    data: [],
                    yAxisID: 'temperature-axis'
                },
                {
                    label: 'Power',
                    fill: true,
                    backgroundColor: 'rgba(75, 192, 192,0.3)',
					borderColor: chartColors.green,
                    data: [],
                    yAxisID: 'power-axis'
                },
                {
                    label: 'Setpoint',
                    fill: false,
                    backgroundColor: chartColors.blue,
					borderColor: chartColors.blue,
                    data: [],
                    yAxisID: 'temperature-axis'
                }
                ]
            },
            options: {
                scales: {
                    xAxes: [{
                        type: 'time',
                        time: {
                            unit: 'minute',
                            stepSize: 5,
                            displayFormats: {
                            //    'millisecond': 'HH:MM:SS',
                            //    'second': 'HH:MM:SS',
                               minute: "LTS",
                            //    'hour': 'HH:MM:SS',
                            //    'day': 'HH:MM:SS',
                            //    'week': 'HH:MM:SS',
                            //    'month': 'HH:MM:SS',
                            //    'quarter': 'HH:MM:SS',
                            //    'year': 'HH:MM:SS',
                            }
                        },
						//distribution: 'series',
					}],
                    yAxes: [{
                            beginAtZero:false,
                            position: 'left',
                            id: 'temperature-axis'
                        },{
                            beginAtZero:true,
                            ticks: {
                                suggestedMin: 0,
                                suggestedMax: 100
                            },
                            position: 'right',
                            id: 'power-axis'
                        },
                        {
                            beginAtZero:false,
                            ticks: {
                                suggestedMin: 1,
                                suggestedMax: 1.120
                            },
                            position: 'right',
                            id: 'gravity-axis'
                        }]
                }
            }
        });  
        fetch(this.href)
        .then(response=>response.json())
        .then(json =>{
            json.label.forEach(x=>this.chart.data.labels.push(Math.floor(1000*x)))
            json.temperature.forEach(x=>this.chart.data.datasets[0].data.push(x))
            json.power.forEach(x=>this.chart.data.datasets[1].data.push(x))
            json.setpoint.forEach(x=>this.chart.data.datasets[2].data.push(x))
            if (json.gravity != undefined) {
                this.chart.data.datasets.push({
                    label: 'Gravity',
                    fill: true,
                    backgroundColor: chartColors.yellow,
	            borderColor: chartColors.white,
                    data: [],
                    yAxisID: 'gravity-axis'
                })
                json.gravity.forEach(x=>this.chart.data.datasets[3].data.push(x))
            }
            this.chart.update()      
        })
    }
}

Vue.component('brewcontroller', {
    props: ['href'],
    components: {
        'plot': plotComp
    },
    template: `
    <div>
    <b-container>
        <b-row>
            <b-col>{{ controllerState.name }}</b-col>
        </b-row>
        <b-row>
            <b-col>
                <b-button variant="primary" :pressed="controllerState.enabled" @click="enable">{{ enabledStr }}</b-button> 
            </b-col>
        </b-row>
        <b-row align-v="start">
            <b-col col sm="2">Temperature:</label></b-col>
            <b-col col sm="2">{{ formattedTemperature }}</b-col>
        </b-row>
        <b-row>
            <b-col col sm="2"><label for="setpoint">Target:</label></b-col>
            <b-col col sm="2"><b-form-input id="setpoint" v-model="controllerState.setpoint" @change="setpointUpdate"/></b-col>
        </b-row>
        <b-row>
            <b-col col sm="2"><label for="power">Power:</label></b-col>
            <b-col col sm="2"> {{ formattedPower }}% <b-form-input id="power" type="range" v-model.number.lazy="controllerState.power" @change="updatePower"></b-form-input></b-col>
        </b-row>
        <b-row align-v="start">
            <b-col col sm="2"><b-button variant="success" :pressed="controllerState.automatic" @click="automatic">{{ automaticStr }}</b-button></b-col>
            <b-col col sm="2"><b-button variant="success" :pressed="controllerState.agitating" @click="agitating">{{ agitatedStr }}</b-button></b-col>
        </b-row>
        <b-row>
            <b-col col sm="2" md="6">
                <plot ref="chart" :href="this.href + '/datahistory'"></plot>
            </b-col>
        </b-row>
        </b-container>
    </div>`,
    data: function() {
        return {
            start: Date.now(),
            ws: null,
            ws_connfail: 0,
            controllerState: {}
        }
    },
    computed: {
        formattedTemperature: function() {
            if ('temperature' in this.controllerState)
                return this.controllerState.temperature.toFixed(2)+'\u00B0C'
        },
        formattedPower: function() {
            if ('power' in this.controllerState) {
                return this.controllerState.power.toFixed(0)
            }
        },
        formattedGravity: function() {
            if ('gravity' in this.controllerState)
                return this.controllerState.gravity.toFixed(3)
        },
        enabledStr: function() {
            return this.controllerState.enabled?"Enabled":"Disabled"
        },
        automaticStr: function() {
            return this.controllerState.automatic?"Automatic":"Manual"
        },
        agitatedStr: function() {
            return this.controllerState.agitating?"Agitating":"Still"
        }
    },
    methods: {
        updatePower: function(p) {
            this.ws.send(JSON.stringify({'power': p}))
        },
        newWsConn: function(url) {
            this.ws = new SockJS(url);
            // sock.onopen = function() {
            //     console.log('open');
            // };
        
            this.ws.onmessage = msg=> {
                for (key in msg.data) {
                    this.controllerState[key] = msg.data[key];
                }
                var datapoint = {'when': moment(), 
                                 'temperature': this.controllerState.temperature,
                                 'power': this.controllerState.power, 
                                 setpoint: this.controllerState.setpoint}
                if ('gravity' in this.controllerState)
                    datapoint['gravity'] = this.controllerState.gravity
                this.$refs.chart.newData(datapoint)
            };
            this.ws.onclose = (e) => {
                console.log("WS Close")
                console.log(e)
               this.newWsConn(url);
            };
            this.ws.onerror = (e) => {
                console.log("WS Error: " + e)
            }               
        },
        enable: function () {
            this.ws.send(JSON.stringify({'enabled': !this.controllerState.enabled}))
        },
        automatic: function () {
            this.ws.send(JSON.stringify({'automatic': !this.controllerState.automatic}))
        },
        agitating: function () {
            this.ws.send(JSON.stringify({'agitating': !this.controllerState.agitating}))
        },
        setpointUpdate: function(value) {
            this.controllerState.setpoint = value
            this.ws.send(JSON.stringify({'setpoint': value}))
        }

    },
    mounted: function () {
        fetch(this.href)
        .then(response=>response.json())
        .then(json =>{
            this.controllerState = json
            this.newWsConn(this.controllerState.wsUrl)
        })
    }   
})




var app = new Vue({
    el: '#app',
    data: {
        'controllers': {}
    },
    created: function () {
        fetch('/controllers')
        .then(response=>response.json())
        .then(json=>{
            this.controllers = json
        })
    }
  });

